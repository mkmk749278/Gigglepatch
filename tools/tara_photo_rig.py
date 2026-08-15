"""Build Tara's rig from the real generated artwork.

`tara_rig.py` draws her in code as flat placeholder shapes. This module builds
the same character out of the PNGs `autorig.py` cut from the A-pose, so the
finished animation carries the generated render instead of the stand-in.

The trick that makes the assembly exact
    `autorig` records, for every part, the box it was cut from in the source
    image. So a joint can be named once in *source* coordinates — "the left
    shoulder is at (torso_x0, shoulder_y)" — and each part's pivot and its
    attach point in the parent both fall out of that one number by subtracting
    the relevant box origin.

    The consequence is that a pose with every rotation at zero reassembles the
    original picture pixel for pixel. Any visible seam in that frame is a real
    error, not an eyeballing mistake, which is what makes the assembly check
    worth running before animating anything.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from puppet import Part, Rig                                   # noqa: E402

PARTS_DIR = 'series-tara/reference/parts/body'
PROPS_DIR = 'series-tara/reference/parts'


def _load(meta_dir, name):
    return Image.open(os.path.join(meta_dir, f'{name}.png')).convert('RGBA')


def _far_point(im, origin, ignore_side=None, margin=10):
    """The opaque pixel furthest from `origin` — the hand at the end of an arm.

    `ignore_side` masks off a margin of columns on the side where the crop
    overlaps the torso. Without it the few pixels of tunic caught in that
    overlap run the full height of the crop and sit further from the shoulder
    than the hand does, so the lantern ends up hanging at hip level.
    """
    a = np.asarray(im)[..., 3] > 40
    if ignore_side == 'left':
        a[:, :margin] = False
    elif ignore_side == 'right':
        a[:, -margin:] = False
    ys, xs = np.nonzero(a)
    if xs.size == 0:
        return (im.width // 2, im.height // 2)
    d = (xs - origin[0]) ** 2 + (ys - origin[1]) ** 2
    i = int(np.argmax(d))
    return (int(xs[i]), int(ys[i]))


def _split_limb(im, root, tip, frac=0.5, overlap=7, feather=1.6):
    """Cut a limb into two pieces at a joint, across the limb's own axis.

    A horizontal cut is wrong for anything drawn at an angle — an A-pose arm
    runs diagonally, so a horizontal line slices it lengthwise. This projects
    every pixel onto the root-to-tip axis and cuts across it, which works at
    any angle the limb happens to have been drawn at.

    Both halves are returned on the *original canvas*, uncropped. That is what
    makes the rebuild exact: the joint has the same coordinates in both pieces,
    so it serves as the child's pivot and its attach point in the parent
    without any bookkeeping, and a zero-rotation pose reproduces the source.

    The pieces overlap by a few pixels either side of the cut so the joint does
    not open a gap when it bends.
    """
    ax, ay = tip[0] - root[0], tip[1] - root[1]
    length = float(np.hypot(ax, ay)) or 1.0
    ux, uy = ax / length, ay / length
    cut = frac * length

    h, w = im.height, im.width
    xs = np.arange(w)[None, :] - root[0]
    ys = np.arange(h)[:, None] - root[1]
    proj = xs * ux + ys * uy                       # distance along the limb

    a = np.asarray(im)[..., 3].astype(np.float32)
    upper = np.asarray(im).copy()
    lower = np.asarray(im).copy()
    # smooth ramps rather than hard edges, so the seam does not alias
    up_k = np.clip((cut + overlap - proj) / feather, 0, 1)
    lo_k = np.clip((proj - (cut - overlap)) / feather, 0, 1)
    upper[..., 3] = (a * up_k).astype(np.uint8)
    lower[..., 3] = (a * lo_k).astype(np.uint8)

    joint = (root[0] + ux * cut, root[1] + uy * cut)
    return (Image.fromarray(upper), Image.fromarray(lower), joint)


def build_rig(parts_dir=PARTS_DIR, props_dir=PROPS_DIR, lit_points=0,
              height=None):
    """Assemble the photo rig. Returns a Rig whose zero pose is the source image."""
    meta = json.load(open(os.path.join(parts_dir, 'rig.json')))
    lm = meta['landmarks']
    boxes = {n: p['box'] for n, p in meta['parts'].items()}

    cx = lm['cx']
    tx0, tx1 = lm['torso_x']
    neck_y, sh_y, hip_y = lm['neck_y'], lm['shoulder_y'], lm['hip_y']
    span = lm['bottom'] - lm['top']

    # Joints, named once in source-image coordinates.
    joints = {
        'torso': (cx, neck_y),
        'head': (cx, neck_y),
        'arm_l': (tx0 + int(span * 0.012), sh_y + int(span * 0.02)),
        'arm_r': (tx1 - int(span * 0.012), sh_y + int(span * 0.02)),
        'leg_l': (cx - (tx1 - tx0) // 5, hip_y),
        'leg_r': (cx + (tx1 - tx0) // 5, hip_y),
    }

    def local(name):
        """A joint in source coords, expressed in that part's own image pixels."""
        bx, by = boxes[name][0], boxes[name][1]
        jx, jy = joints[name]
        return (jx - bx, jy - by)

    def attach(name, parent):
        """The same joint, expressed in the parent's image pixels."""
        bx, by = boxes[parent][0], boxes[parent][1]
        jx, jy = joints[name]
        return (jx - bx, jy - by)

    images = {n: _load(parts_dir, n) for n in joints}
    scale = (height / float(span)) if height else 1.0

    rig = Rig(root_pos=(960, 540))
    rig.tag = 'tara'
    rig.scale = scale
    rig.source_span = span
    # The root's pivot is the neck, not the top of the head, so a caller asking
    # for a given figure height needs to know how far down the neck sits.
    rig.neck_frac = (neck_y - lm['top']) / float(span)
    rig.foot_drop = (lm['bottom'] - neck_y) * scale

    # torso is the root; everything else hangs off it
    rig.add(Part('torso', images['torso'], local('torso'), z=40))

    # Legs split at the knee. The thigh keeps the name `leg_*` so every
    # animation already written against it drives the hip exactly as before,
    # and the shin is new.
    for side, z in (('l', 20), ('r', 21)):
        nm = f'leg_{side}'
        hip = local(nm)
        foot = _far_point(images[nm], hip)
        thigh, shin, knee = _split_limb(images[nm], hip, foot, frac=0.48)
        rig.add(Part(nm, thigh, hip, 'torso', attach(nm, 'torso'), z=z))
        rig.add(Part(f'shin_{side}', shin, knee, nm, knee, z=z))

    # Arms split at the elbow. Elbow bend is what does the readability work: a
    # straight arm reads as pointing, a bent one as waving or holding.
    #
    # Her left arm is the gesturing arm and draws in front of the torso, behind
    # the head. Behind the torso it would open a visible gap at the shoulder as
    # soon as it swung up — in front, the arm covers its own joint.
    hands = {}
    for side, z in (('l', 45), ('r', 60)):
        nm = f'arm_{side}'
        shoulder = local(nm)
        # each arm crop overlaps the torso on the side it was cut from
        ignore = 'right' if side == 'l' else 'left'
        hand = _far_point(images[nm], shoulder, ignore_side=ignore)
        upper, fore, elbow = _split_limb(images[nm], shoulder, hand, frac=0.46)
        rig.add(Part(nm, upper, shoulder, 'torso', attach(nm, 'torso'), z=z))
        rig.add(Part(f'fore_{side}', fore, elbow, nm, elbow, z=z + 1))
        hands[side] = hand

    rig.add(Part('head', images['head'], local('head'), 'torso',
                 attach('head', 'torso'), z=50))

    # the lantern hangs from the hand — now a child of the forearm, so it
    # follows the elbow as well as the shoulder
    lan = os.path.join(props_dir, f'lantern_{max(0, min(3, lit_points))}.png')
    if os.path.exists(lan):
        lim = Image.open(lan).convert('RGBA')
        target = int(span * 0.16)
        if lim.height > target:
            k = target / lim.height
            lim = lim.resize((max(int(lim.width * k), 1), target), Image.LANCZOS)
        rig.add(Part('lantern', lim, (lim.width // 2, int(lim.height * 0.06)),
                     'fore_r', hands['r'], z=70))

    return rig


def assembly_check(out='assembly_check.png', size=(1920, 1080), bg=(24, 24, 28)):
    """Render every rotation at zero. Any seam here is a real pivot error."""
    h = int(size[1] * 0.86)
    rig = build_rig(height=h)
    top = (size[1] - h) // 2
    rig.root_pos = (size[0] // 2, top + rig.neck_frac * h)
    # Scale is inherited down the hierarchy, so it goes on the root only —
    # setting it on every part multiplies it once per level of nesting.
    frame = rig.render({'torso': {'scale': rig.scale}}, size)
    out_im = Image.new('RGBA', size, bg + (255,))
    out_im.alpha_composite(frame)
    out_im.convert('RGB').save(out, quality=95)
    return out


def call_out_shot(out="tara_callout.mp4", seconds=10.0, fps=30,
                  size=(1920, 1080)):
    """The CALL-OUT PAUSE, rendered with the real artwork on a real background.

    The animation itself is `tara_rig.call_out_pause()`, unchanged. That is the
    payoff of a rig: performance is written against part names and angles, so
    swapping placeholder shapes for generated art changes how the shot looks and
    nothing about how it works.

    Two of that animation's tracks address parts this rig does not have — the
    forearms and the braids, which the A-pose gives us fused into the arm and
    hidden behind the head. Tracks for missing parts are simply ignored, so the
    arm swings from the shoulder as one piece. Add an elbow and the same
    animation gains the bend with no edit here.
    """
    import scenes
    import finish
    from puppet import render_video
    from tara_rig import call_out_pause

    h = int(size[1] * 0.60)
    rig = build_rig(height=h)
    ground = int(size[1] * 0.90)
    rig.root_pos = (int(size[0] * 0.50), ground - rig.foot_drop)

    stage = finish.soften(scenes.banyan_court(scenes.MORNING, size=size))
    finish.contact_shadow(stage, rig.root_pos[0], ground - h * 0.012, h * 0.17)

    anim = call_out_pause()
    anim.track('torso', 'scale', [(0, rig.scale), (seconds, rig.scale)])

    render_video(rig, anim, out, seconds, fps=fps, size=size,
                 background=stage, extra=finish.Grade(size))
    return out


def wave_shot(out='tara_wave.mp4', seconds=5.0, fps=30, size=(1920, 1080)):
    """Tara waving hello, finished so she sits *in* the shot rather than on it.

    30fps rather than 24. Cut-out animation has no motion blur, so the judder
    that film gets away with is much more visible here — the extra six frames a
    second cost nothing and are the cheapest smoothness available.
    """
    import scenes
    import finish
    from puppet import render_video
    from tara_rig import wave_hello

    h = int(size[1] * 0.66)
    rig = build_rig(height=h)
    ground = int(size[1] * 0.93)
    rig.root_pos = (int(size[0] * 0.50), ground - rig.foot_drop)

    stage = finish.soften(scenes.courtyard(scenes.MORNING, size=size))
    finish.contact_shadow(stage, rig.root_pos[0], ground - h * 0.012, h * 0.17)

    anim = wave_hello(seconds)
    anim.track('torso', 'scale', [(0, rig.scale), (seconds, rig.scale)])

    grade = finish.Grade(size)
    render_video(rig, anim, out, seconds, fps=fps, size=size,
                 background=stage, extra=grade)
    return out


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'assembly'
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == 'callout':
        print('wrote', call_out_shot(dst or 'tara_callout.mp4'))
    elif mode == 'wave':
        print('wrote', wave_shot(dst or 'tara_wave.mp4'))
    else:
        print('wrote', assembly_check(dst or 'assembly_check.png'))
