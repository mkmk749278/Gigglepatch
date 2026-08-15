"""Cut-out puppet animation — the technique Dora was actually made with.

A character is built once as a rig of separate pieces connected in a hierarchy
(head hangs off torso, forearm hangs off upper arm). Animation is then a matter
of rotating and moving those pieces over time. The artwork never changes, so the
character physically cannot drift, flicker or age between frames — the failure
modes that make per-frame image generation unusable simply do not exist here.

This module is the engine. Art and animation are supplied by the caller; see
tara_rig.py for a worked example.

Coordinates
    Every part carries two points:
      pivot  — where it rotates, in its OWN image pixels
      attach — where that pivot sits, in its PARENT's image pixels
    A part with no parent is placed directly in canvas pixels.
"""
import math
import subprocess
from dataclasses import dataclass, field

from PIL import Image


@dataclass
class Part:
    """One piece of artwork in the rig."""
    name: str
    image: Image.Image
    pivot: tuple                     # (x, y) in this part's own image
    parent: str = None
    attach: tuple = (0, 0)           # (x, y) in the parent's image
    z: int = 0                       # draw order, low to high


@dataclass
class Rig:
    parts: dict = field(default_factory=dict)
    root_pos: tuple = (0, 0)         # where the root part's pivot sits on canvas

    def add(self, part):
        self.parts[part.name] = part
        return part

    def order(self):
        return sorted(self.parts.values(), key=lambda p: p.z)

    def world(self, pose):
        """Resolve every part to an absolute (x, y, angle, scale) on canvas.

        pose maps part name -> dict(rot=deg, dx=, dy=, scale=), all optional.
        A part inherits its parent's rotation and scale, which is what makes a
        hierarchy useful: rotate the torso and the head, arms and braids all
        follow without being animated individually.
        """
        out = {}

        def resolve(name):
            if name in out:
                return out[name]
            p = self.parts[name]
            local = pose.get(name, {})
            rot = math.radians(local.get('rot', 0.0))
            scale = local.get('scale', 1.0)
            dx, dy = local.get('dx', 0.0), local.get('dy', 0.0)

            if p.parent is None:
                x = self.root_pos[0] + dx
                y = self.root_pos[1] + dy
                return out.setdefault(name, (x, y, rot, scale))

            px, py, pang, pscale = resolve(p.parent)
            parent = self.parts[p.parent]
            # where this part's attach point lands, in canvas space
            ox = (p.attach[0] - parent.pivot[0]) * pscale
            oy = (p.attach[1] - parent.pivot[1]) * pscale
            ca, sa = math.cos(pang), math.sin(pang)
            x = px + ca * ox - sa * oy + dx
            y = py + sa * ox + ca * oy + dy
            return out.setdefault(name, (x, y, pang + rot, pscale * scale))

        for n in self.parts:
            resolve(n)
        return out

    def render(self, pose, size, background=None):
        """Composite the whole rig into one frame."""
        canvas = (background.copy() if background is not None
                  else Image.new('RGBA', size, (0, 0, 0, 0)))
        placed = self.world(pose)
        for part in self.order():
            x, y, ang, scale = placed[part.name]
            layer = _transform(part.image, part.pivot, (x, y), ang, scale, size)
            canvas.alpha_composite(layer)
        return canvas


def _transform(img, pivot, world, angle, scale, size):
    """Place `img` so its pivot sits at `world`, rotated and scaled.

    PIL's AFFINE maps output pixels back to input pixels, so this is the
    inverse transform: undo the translation, then the rotation, then the scale.
    """
    if scale <= 1e-6:
        return Image.new('RGBA', size, (0, 0, 0, 0))
    ca, sa = math.cos(angle), math.sin(angle)
    inv = 1.0 / scale
    a, b = ca * inv, sa * inv
    d, e = -sa * inv, ca * inv
    c = pivot[0] - (a * world[0] + b * world[1])
    f = pivot[1] - (d * world[0] + e * world[1])
    return img.transform(size, Image.AFFINE, (a, b, c, d, e, f),
                         resample=Image.BICUBIC)


# --------------------------------------------------------------------------
# timing
# --------------------------------------------------------------------------
def ease(t):
    """Smoothstep. Real movement accelerates and settles; it never starts or
    stops at full speed, which is what makes linear interpolation look robotic."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ease_out_back(t, overshoot=1.4):
    """Settles slightly past the target then comes back — the small
    overshoot that makes a gesture feel alive rather than mechanical."""
    t = min(max(t, 0.0), 1.0)
    t -= 1.0
    return 1 + t * t * ((overshoot + 1) * t + overshoot)


class Track:
    """Keyframes for one channel of one part, e.g. the head's rotation."""

    def __init__(self, keys, easing=ease):
        self.keys = sorted(keys)          # [(time_seconds, value), ...]
        self.easing = easing

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                span = t1 - t0
                u = self.easing((t - t0) / span) if span > 1e-9 else 1.0
                return v0 + (v1 - v0) * u
        return ks[-1][1]


class Animation:
    """All tracks for a rig, sampled to a pose at any moment."""

    def __init__(self):
        self.tracks = {}              # (part, channel) -> Track

    def track(self, part, channel, keys, easing=ease):
        self.tracks[(part, channel)] = Track(keys, easing)
        return self

    def pose(self, t):
        pose = {}
        for (part, channel), tr in self.tracks.items():
            pose.setdefault(part, {})[channel] = tr.at(t)
        return pose


# --------------------------------------------------------------------------
# camera
# --------------------------------------------------------------------------
class Camera:
    """A moving window over a larger stage.

    The scene is composited at stage resolution and the camera crops a window
    out of it, so a push-in samples down from real pixels instead of upscaling.
    Keyframe x and y (the window centre, in stage pixels) and zoom, where zoom
    above 1 is closer.
    """

    def __init__(self, stage, out):
        self.stage = stage
        self.out = out
        self.tracks = {}

    def track(self, channel, keys, easing=ease):
        self.tracks[channel] = Track(keys, easing)
        return self

    def at(self, t):
        sw, sh = self.stage
        z = self.tracks['zoom'].at(t) if 'zoom' in self.tracks else 1.0
        cx = self.tracks['x'].at(t) if 'x' in self.tracks else sw / 2
        cy = self.tracks['y'].at(t) if 'y' in self.tracks else sh / 2
        ow, oh = self.out
        # widest window of the output aspect that fits the stage, then zoomed
        w = min(sw, sh * ow / oh) / z
        h = w * oh / ow
        cx = min(max(cx, w / 2), sw - w / 2)
        cy = min(max(cy, h / 2), sh - h / 2)
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def apply(self, frame, t):
        return frame.resize(self.out, Image.LANCZOS, box=self.at(t))


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def render_shot(rigs, out_size, t, background=None, camera=None):
    """Composite one frame: background, then every rig, then the camera crop.

    `rigs` is a list of (rig, animation) pairs, drawn in order.
    """
    stage = camera.stage if camera else out_size
    bg = background(t) if callable(background) else background
    frame = (bg.copy() if bg is not None
             else Image.new('RGBA', stage, (0, 0, 0, 0)))
    for rig, anim in rigs:
        placed = rig.world(anim.pose(t))
        for part in rig.order():
            x, y, ang, scale = placed[part.name]
            frame.alpha_composite(
                _transform(part.image, part.pivot, (x, y), ang, scale, stage))
    return camera.apply(frame, t) if camera else frame


def render_video(rig, anim, out, seconds, fps=24, size=(1920, 1080),
                 background=None, extra=None, verbose=True):
    """Render the animation straight into an MP4 through ffmpeg.

    `background` may be a still Image or a callable(t) -> Image. The callable
    form is what makes a walk work: the character cycles in place and the
    background slides past, which is how cut-out shows have always handled
    journeys without animating forward travel.
    """
    n = int(round(seconds * fps))
    proc = subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{size[0]}x{size[1]}', '-r', str(fps), '-i', 'pipe:0',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
        stdin=subprocess.PIPE)

    for i in range(n):
        t = i / fps
        bg = background(t) if callable(background) else background
        frame = rig.render(anim.pose(t), size, background=bg)
        if extra is not None:
            extra(frame, t, i)
        proc.stdin.write(frame.convert('RGB').tobytes())
        if verbose and i % fps == 0:
            print(f'  {t:4.1f}s / {seconds:.1f}s', flush=True)

    proc.stdin.close()
    proc.wait()
    if verbose:
        print(f'wrote {out}  ({n} frames @ {fps}fps)')
    return out
