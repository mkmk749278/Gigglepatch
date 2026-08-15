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

    rig.add(Part('leg_l', images['leg_l'], local('leg_l'), 'torso',
                 attach('leg_l', 'torso'), z=20))
    rig.add(Part('leg_r', images['leg_r'], local('leg_r'), 'torso',
                 attach('leg_r', 'torso'), z=21))

    # her left arm reads as the far arm, so it sits behind the body
    rig.add(Part('arm_l', images['arm_l'], local('arm_l'), 'torso',
                 attach('arm_l', 'torso'), z=10))
    rig.add(Part('arm_r', images['arm_r'], local('arm_r'), 'torso',
                 attach('arm_r', 'torso'), z=60))

    rig.add(Part('head', images['head'], local('head'), 'torso',
                 attach('head', 'torso'), z=50))

    # the lantern hangs from whichever point of the near arm is furthest from
    # the shoulder — which is the hand, whatever angle the arm was drawn at
    lan = os.path.join(props_dir, f'lantern_{max(0, min(3, lit_points))}.png')
    if os.path.exists(lan):
        lim = Image.open(lan).convert('RGBA')
        target = int(span * 0.16)
        if lim.height > target:
            k = target / lim.height
            lim = lim.resize((max(int(lim.width * k), 1), target), Image.LANCZOS)
        # arm_r's crop overlaps the torso on its left edge, so ignore it there
        hand = _far_point(images['arm_r'], local('arm_r'), ignore_side='left')
        rig.add(Part('lantern', lim, (lim.width // 2, int(lim.height * 0.06)),
                     'arm_r', hand, z=70))

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


def call_out_shot(out='tara_callout.mp4', seconds=10.0, fps=24,
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
    from puppet import render_video
    from tara_rig import call_out_pause

    h = int(size[1] * 0.60)
    rig = build_rig(height=h)
    ground = int(size[1] * 0.90)
    rig.root_pos = (int(size[0] * 0.50), ground - rig.foot_drop)

    stage = scenes.banyan_court(scenes.MORNING, size=size)
    anim = call_out_pause()
    anim.track('torso', 'scale', [(0, rig.scale), (seconds, rig.scale)])

    render_video(rig, anim, out, seconds, fps=fps, size=size, background=stage)
    return out


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'assembly'
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == 'callout':
        print('wrote', call_out_shot(dst or 'tara_callout.mp4'))
    else:
        print('wrote', assembly_check(dst or 'assembly_check.png'))
