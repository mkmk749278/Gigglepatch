"""Shot renderer: rig + backdrop + light + camera -> frames -> mp4.

Motion blur is done properly rather than faked: the take is evaluated at
`samples` times the output rate and the sub-frames inside the shutter window are
averaged.  That is what stops a 24fps cutout from strobing, and it is the single
biggest difference between "a sequence of drawings" and "footage".
"""

from __future__ import annotations

import os
import subprocess

import numpy as np
from scipy import ndimage

from . import anim, face, rig, scene

FPS = 24
SIZE = (1280, 720)  # w, h
GROUND_Y = 566
SAMPLES = 3
SHUTTER = 0.62


def root_matrix(scale: float, tx: float, ty: float) -> np.ndarray:
    return np.array([[scale, 0.0, tx], [0.0, scale, ty], [0.0, 0.0, 1.0]], np.float32)


def character_fit(w: int, h: int, height_frac: float = 0.70) -> tuple[float, float, float]:
    """Scale and place the plate so her soles land on the ground line."""
    scale = (h * height_frac) / 641.0
    tx = w * 0.44 - 250.0 * scale
    ty = GROUND_Y - 628.0 * scale
    return scale, tx, ty


def lantern_light(shape, centre, radius, colour, strength) -> np.ndarray:
    """Additive radial falloff -- the lantern actually lighting the shot.

    Inverse-square-ish rather than a clipped linear ramp: a ramp that reaches
    zero at a finite radius draws a visible disc edge across whatever is behind
    it, which was the hard-edged bubble in the first pass.
    """
    h, w = shape
    y, x = np.ogrid[0:h, 0:w]
    d2 = ((x - centre[0]) ** 2 + (y - centre[1]) ** 2) / (radius * radius)
    fall = 1.0 / (1.0 + 5.5 * d2) ** 1.6
    return fall[..., None] * (np.array(colour, np.float32) * strength)


def ground_pool(shape, centre, radius, colour, strength) -> np.ndarray:
    """The same light landing on the street.

    Centred on the ground under the lantern, not at the lantern's own height --
    light pools where it lands.
    """
    h, w = shape
    y, x = np.ogrid[0:h, 0:w]
    cy = GROUND_Y + 34
    d = np.sqrt(((x - centre[0]) / radius) ** 2 + ((y - cy) / (radius * 0.30)) ** 2)
    fall = 1.0 / (1.0 + 4.0 * d * d) ** 1.5
    fall = fall * np.clip((y - GROUND_Y + 26) / 26.0, 0.0, 1.0)
    return fall[..., None] * (np.array(colour, np.float32) * strength)


def contact_shadow(shape, world_pts, strength=0.82) -> np.ndarray:
    """Soft ellipse under each foot -- without it she floats.

    The shadow tightens and darkens as the foot nears the ground and spreads out
    as it lifts, which is what actually tells the eye where the floor is.
    """
    h, w = shape
    y, x = np.ogrid[0:h, 0:w]
    acc = np.zeros((h, w), np.float32)
    for (cx, cy), rad in world_pts:
        lift = np.clip(1.0 - (GROUND_Y - cy) / 44.0, 0.18, 1.0)
        spread = rad * (2.0 - lift)
        d = np.sqrt(((x - cx) / spread) ** 2 + ((y - GROUND_Y - 8) / (spread * 0.34)) ** 2)
        acc = np.maximum(acc, np.clip(1.0 - d, 0.0, 1.0) ** 1.5 * lift)
    return 1.0 - acc[..., None] * strength


def bloom(img: np.ndarray, threshold: float = 0.72, amount: float = 0.42) -> np.ndarray:
    bright = np.clip(img - threshold, 0.0, None)
    glow = np.dstack([ndimage.gaussian_filter(bright[..., c], 13.0) for c in range(3)])
    glow += np.dstack([ndimage.gaussian_filter(bright[..., c], 42.0) for c in range(3)]) * 0.6
    return img + glow * amount


def vignette(shape, strength=0.34) -> np.ndarray:
    h, w = shape
    y, x = np.ogrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w * 0.62)) ** 2 + ((y - h / 2) / (h * 0.66)) ** 2)
    return (1.0 - np.clip(d - 0.35, 0.0, 1.0) ** 1.8 * strength)[..., None]


def grain(shape, rng, amount=0.012) -> np.ndarray:
    n = rng.normal(0.0, amount, (shape[0], shape[1], 1)).astype(np.float32)
    return np.repeat(ndimage.gaussian_filter(n, (0.7, 0.7, 0)), 3, axis=2)


def world_point(parts, pose, part_name, local, root) -> tuple[float, float]:
    m = root @ rig.world_transforms(parts, pose)[part_name]
    p = m @ np.array([local[0], local[1], 1.0], np.float32)
    return float(p[0]), float(p[1])


def render_shot(out_dir: str, seconds: float = 6.0, fps: int = FPS, size=SIZE,
                samples: int = SAMPLES, plate: str = "assets/dora/plates/pose_walking.png"):
    w, h = size
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(3)

    parts = rig.build(plate)
    head_base = parts["head"].rgba
    scale, tx, ty = character_fit(w, h)
    frames = int(round(seconds * fps))
    sub = frames * samples
    take = anim.WalkTake(sub, fps=fps * samples)
    speed = anim.ground_speed(take.cycle) * scale

    backdrop = scene.Backdrop(w, h, span=4)
    vig = vignette((h, w))
    shutter_n = max(1, int(round(samples * SHUTTER)))

    for i in range(frames):
        acc = np.zeros((h, w, 3), np.float32)
        for k in range(shutter_n):
            s = i * samples + k
            acc += _render_sub(parts, head_base, take, s, backdrop, speed, scale, tx, ty,
                               (h, w), fps * samples)
        img = acc / shutter_n

        img = bloom(img)
        img *= vig
        img += grain((h, w), rng)
        out = (np.clip(img, 0.0, 1.0) ** (1 / 1.02) * 255.0).astype(np.uint8)
        _save(out, os.path.join(out_dir, f"f{i:04d}.png"))
    return frames


def _render_sub(parts, head_base, take, s, backdrop, speed, scale, tx, ty, shape, subfps):
    h, w = shape
    t = s / subfps
    # She travels screen-left, so the world must slide right past camera.
    scroll = -speed * t

    # Camera: a very slow push-in plus a breath of handheld drift.
    push = 1.0 + 0.030 * (t / max(take.frames / subfps, 1e-3))
    dx = 2.2 * np.sin(t * 0.9) + 1.1 * np.sin(t * 2.3)
    dy = 1.6 * np.sin(t * 0.7 + 1.1)
    root = root_matrix(scale * push, tx + dx - (push - 1) * w * 0.44, ty + dy - (push - 1) * h * 0.55)

    pose = take.pose(s)
    parts["head"].rgba = face.blink(head_base, float(take.blink[s]))
    layer = rig.render(parts, pose, (h, w), root=root)

    lx, ly = world_point(parts, pose, "lantern", (100.0, 447.0), root)
    feet = [
        (world_point(parts, pose, "front_shin", (180.0, 606.0), root), 30.0 * scale * push),
        (world_point(parts, pose, "back_shin", (398.0, 596.0), root), 29.0 * scale * push),
    ]

    bg = backdrop.frame(scroll)[..., :3]
    bg = bg * contact_shadow((h, w), feet)
    bg = bg + ground_pool((h, w), (lx, ly), 340.0, (1.0, 0.70, 0.34), 0.72)

    # Warm key from the lantern onto the character, strongest nearest to it.
    a = layer[..., 3:4]
    key = lantern_light((h, w), (lx, ly), 330.0, (1.0, 0.74, 0.42), 0.55)
    char = layer[..., :3] + key * a * 0.9

    img = char + bg * (1.0 - a)
    # The lamp's own halo in the air, on top of everything.
    img = img + lantern_light((h, w), (lx, ly), 190.0, (1.0, 0.80, 0.50), 0.40)

    # Defocused foreground: motes drifting between camera and subject.  Cheap,
    # and it does more for the sense of a real lens than anything else here.
    fg = backdrop.foreground(scroll)
    img = img * (1.0 - fg[..., 3:4] * 0.55) + fg[..., :3] * fg[..., 3:4] * 0.75
    return img


def _save(arr, path):
    from PIL import Image

    Image.fromarray(arr).save(path, compress_level=1)


def encode(frame_dir: str, out_path: str, fps: int = FPS, crf: int = 17):
    import imageio_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y", "-framerate", str(fps), "-i", os.path.join(frame_dir, "f%04d.png"),
           "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
