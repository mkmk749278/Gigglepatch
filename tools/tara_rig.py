"""Tara built as a cut-out puppet, and the CALL-OUT PAUSE animated.

The artwork here is drawn in code as flat placeholder shapes so the pipeline
runs today with nothing to download. It is deliberately simple — its job is to
prove the rig, the hierarchy and the timing, not to be the finished look.

To swap in real art, replace each _draw_* function with a PNG loaded from
series-tara/reference/parts/. Keep the pivot and attach points and every
animation in this file keeps working unchanged. That separation is the whole
point of a rig: art and performance are independent.
"""
import math
import os
import sys

import cv2
import numpy as np

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from puppet import Animation, Part, Rig, ease, ease_out_back, render_video

# Palette straight from the character bible
SKIN = (198, 140, 96, 255)
SKIN_SH = (176, 120, 80, 255)
HAIR = (28, 22, 26, 255)
KURTA = (32, 138, 130, 255)      # teal-green
KURTA_SH = (24, 112, 106, 255)
CHURIDAR = (246, 244, 238, 255)  # white
SHOE = (198, 62, 52, 255)        # red canvas
RIBBON = (247, 181, 41, 255)     # marigold yellow
BRASS = (204, 152, 62, 255)
BRASS_LT = (238, 198, 108, 255)
GLOW = (255, 214, 130, 255)
INK = (38, 28, 24, 255)


def _img(w, h):
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))


def _volumize(im, light=(-0.55, -0.8), volume=0.34, rim=0.30, shadow=0.26):
    """Turn a flat filled shape into something that reads as rounded.

    The distance transform of the alpha channel gives, for every pixel, how far
    it sits from the silhouette edge. That field is effectively a fake normal
    map: high in the middle of a limb, zero at its outline. Brightening by it
    produces cylindrical shading, and offsetting it toward the light produces a
    lit side and a shaded side.

    It is not real 3D — there is no geometry here — but it is the difference
    between artwork that reads as paper and artwork that reads as form.
    """
    arr = np.asarray(im).astype(np.float32)
    a = arr[..., 3]
    if a.max() <= 0:
        return im
    mask = (a > 8).astype(np.uint8)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    if dist.max() <= 0:
        return im
    dist /= dist.max()
    # The raw field ridges along the medial axis, which prints a visible crease
    # down the middle of any boxy shape. Blurring it turns the ridge back into
    # a smooth bulge.
    k = max(int(min(im.size) * 0.16) | 1, 3)
    dist = cv2.GaussianBlur(dist, (k, k), 0)
    dist /= max(dist.max(), 1e-6)

    # light and shadow come from the same field, sampled either side of centre
    lx, ly = light
    shift = max(int(min(im.size) * 0.09), 3)
    lit = np.roll(np.roll(dist, int(ly * shift), axis=0), int(lx * shift), axis=1)
    dark = np.roll(np.roll(dist, -int(ly * shift), axis=0), -int(lx * shift), axis=1)

    core = 1.0 + volume * (dist - 0.45)                # rounded body
    lo = 1.0 - shadow * np.clip(dark - dist, 0, 1) * 3.0
    hi = rim * np.clip(lit - dist, 0, 1) * 3.0

    rgb = arr[..., :3]
    rgb = rgb * core[..., None] * lo[..., None]
    rgb = rgb + (255.0 - rgb) * np.clip(hi, 0, 1)[..., None]
    out = np.concatenate([np.clip(rgb, 0, 255), a[..., None]], axis=-1)
    return Image.fromarray(out.astype(np.uint8))


# --------------------------------------------------------------------------
# artwork — replace these with real PNGs when you have them
# --------------------------------------------------------------------------
def _draw_head():
    w, h = 320, 340
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.ellipse((40, 30, 280, 290), fill=SKIN)                      # face
    d.ellipse((44, 20, 276, 150), fill=HAIR)                      # hair cap
    d.rectangle((40, 84, 276, 104), fill=HAIR)
    d.ellipse((96, 150, 140, 196), fill=(255, 255, 255, 255))     # eye whites
    d.ellipse((180, 150, 224, 196), fill=(255, 255, 255, 255))
    d.ellipse((106, 160, 132, 190), fill=INK)                     # irises
    d.ellipse((190, 160, 216, 190), fill=INK)
    d.ellipse((112, 165, 121, 174), fill=(255, 255, 255, 255))    # catchlights
    d.ellipse((196, 165, 205, 174), fill=(255, 255, 255, 255))
    d.arc((100, 132, 140, 156), 200, 340, fill=INK, width=5)      # brows
    d.arc((180, 132, 220, 156), 200, 340, fill=INK, width=5)
    d.ellipse((152, 104, 168, 120), fill=(140, 40, 60, 255))      # bindi
    d.arc((124, 196, 196, 246), 20, 160, fill=INK, width=6)       # smile
    d.ellipse((70, 196, 100, 226), fill=(214, 150, 120, 120))     # blush
    d.ellipse((220, 196, 250, 226), fill=(214, 150, 120, 120))
    return im, (160, 290)                                          # pivot at neck


def _draw_braid(flip=False):
    w, h = 90, 300
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    for i, y in enumerate(range(10, 250, 34)):                     # plaited bumps
        r = 40 - i * 2
        d.ellipse((45 - r // 2, y, 45 + r // 2, y + 44), fill=HAIR)
    d.ellipse((28, 244, 62, 278), fill=RIBBON)                     # ribbon
    d.polygon([(45, 262), (18, 296), (72, 296)], fill=RIBBON)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im, (45, 18)


def _draw_torso():
    w, h = 300, 330
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 30, 240, 250), radius=58, fill=KURTA)  # kurta
    d.rounded_rectangle((60, 200, 240, 250), radius=24, fill=KURTA_SH)
    d.ellipse((116, 16, 184, 60), fill=SKIN_SH)                     # neck
    return im, (150, 40)


def _draw_arm(upper=True):
    w, h = 92, 210
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((28, 10, 66, 168), radius=19,
                        fill=KURTA if upper else SKIN)
    if not upper:
        d.ellipse((22, 148, 72, 198), fill=SKIN)                    # hand
    return im, (47, 22)


def _draw_leg():
    w, h = 100, 250
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((30, 10, 72, 190), radius=21, fill=CHURIDAR)
    d.rounded_rectangle((22, 182, 84, 232), radius=18, fill=SHOE)   # shoe
    return im, (51, 22)


def _draw_lantern(lit_points=0):
    # Sized against the torso: a lantern a five-year-old can carry, not a
    # staff. At 200 it dragged on the ground during a walk.
    w = h = 132
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(10):                                             # five-point star
        ang = -math.pi / 2 + i * math.pi / 5
        r = 52 if i % 2 == 0 else 21
        pts.append((66 + r * math.cos(ang), 70 + r * math.sin(ang)))
    d.polygon(pts, fill=BRASS)
    d.line([(66, 18), (66, 6)], fill=BRASS, width=5)                # ring handle
    d.ellipse((56, 0, 76, 16), outline=BRASS, width=5)
    for i in range(5):                                              # the five lights
        ang = -math.pi / 2 + i * 2 * math.pi / 5
        cx, cy = 66 + 35 * math.cos(ang), 70 + 35 * math.sin(ang)
        on = i < lit_points
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8),
                  fill=GLOW if on else BRASS_LT)
    return im, (66, 6)


# --------------------------------------------------------------------------
def build_rig(lit_points=0):
    """Assemble the hierarchy. Rotate the torso and everything above follows."""
    # 560 puts the full figure in frame with headroom; 700 cropped the feet
    rig = Rig(root_pos=(960, 560))
    rig.tag = 'tara'

    # Shading is baked once at build time, not per frame — it costs nothing
    # during the render and every pose inherits the same lighting.
    torso_img, torso_piv = _draw_torso(); torso_img = _volumize(torso_img)
    head_img, head_piv = _draw_head(); head_img = _volumize(head_img, volume=0.26)
    bl_img, bl_piv = _draw_braid(); bl_img = _volumize(bl_img)
    br_img, br_piv = _draw_braid(flip=True); br_img = _volumize(br_img)
    ua_img, ua_piv = _draw_arm(upper=True); ua_img = _volumize(ua_img)
    fa_img, fa_piv = _draw_arm(upper=False); fa_img = _volumize(fa_img)
    leg_img, leg_piv = _draw_leg(); leg_img = _volumize(leg_img)
    lan_img, lan_piv = _draw_lantern(lit_points); lan_img = _volumize(lan_img)

    rig.add(Part('torso', torso_img, torso_piv, z=40))

    rig.add(Part('leg_l', leg_img.copy(), leg_piv, 'torso', (112, 236), z=20))
    rig.add(Part('leg_r', leg_img.copy(), leg_piv, 'torso', (188, 236), z=21))

    # far arm sits behind the body, near arm in front
    rig.add(Part('arm_l', ua_img.copy(), ua_piv, 'torso', (74, 62), z=10))
    rig.add(Part('fore_l', fa_img.copy(), fa_piv, 'arm_l', (47, 168), z=11))
    rig.add(Part('arm_r', ua_img.copy(), ua_piv, 'torso', (226, 62), z=60))
    rig.add(Part('fore_r', fa_img.copy(), fa_piv, 'arm_r', (47, 168), z=61))

    rig.add(Part('head', head_img, head_piv, 'torso', (150, 44), z=50))
    rig.add(Part('braid_l', bl_img, bl_piv, 'head', (66, 120), z=30))
    rig.add(Part('braid_r', br_img, br_piv, 'head', (254, 120), z=31))

    rig.add(Part('lantern', lan_img, lan_piv, 'fore_r', (47, 176), z=70))
    return rig


def _draw_squirrel_body():
    """Sitting upright, seen from the side — the pose a palm squirrel holds
    most of the time. Stripes run down the length of the back."""
    w, h = 130, 165
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.ellipse((30, 34, 112, 150), fill=(150, 128, 104, 255))          # haunch/body
    d.ellipse((44, 22, 104, 96), fill=(158, 136, 112, 255))           # chest
    for i, x in enumerate((60, 76, 92)):                              # three stripes
        d.ellipse((x, 44 + i * 3, x + 9, 128 - i * 4),
                  fill=(238, 226, 200, 255))
    d.ellipse((36, 118, 78, 152), fill=(132, 110, 88, 255))           # hind foot
    d.ellipse((44, 74, 66, 100), fill=(158, 136, 112, 255))           # front paw
    return im, (72, 40)


def _draw_squirrel_head():
    w, h = 104, 104
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    d.ellipse((20, 22, 88, 92), fill=(158, 136, 112, 255))
    d.ellipse((24, 8, 48, 34), fill=(136, 114, 92, 255))              # ears
    d.ellipse((60, 8, 84, 34), fill=(136, 114, 92, 255))
    d.ellipse((30, 12, 44, 28), fill=(196, 168, 150, 255))
    d.ellipse((64, 12, 78, 28), fill=(196, 168, 150, 255))
    d.ellipse((34, 44, 48, 62), fill=INK)                             # eyes
    d.ellipse((58, 44, 72, 62), fill=INK)
    d.ellipse((37, 47, 43, 53), fill=(255, 255, 255, 255))
    d.ellipse((61, 47, 67, 53), fill=(255, 255, 255, 255))
    d.ellipse((46, 64, 60, 76), fill=(212, 148, 150, 255))            # nose
    return im, (54, 86)


def _draw_squirrel_tail():
    """A tapering plume arcing up and back. Sized against the body — a palm
    squirrel's tail is about as long as it is, not three times."""
    w, h = 170, 210
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    base = (118, 190)
    for i in range(16):                                               # outer plume
        f = i / 15.0
        ang = math.radians(-96 + f * 96)                              # arcs backward
        dist = 20 + f * 132
        x = base[0] - dist * math.sin(ang) * 0.85
        y = base[1] - dist * math.cos(ang) * 0.92
        r = 15 + 20 * math.sin(f * math.pi * 0.85)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(160, 138, 112, 255))
    for i in range(12):                                               # lighter core
        f = i / 11.0
        ang = math.radians(-92 + f * 92)
        dist = 24 + f * 116
        x = base[0] - dist * math.sin(ang) * 0.85
        y = base[1] - dist * math.cos(ang) * 0.92
        r = 7 + 9 * math.sin(f * math.pi * 0.8)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(186, 166, 138, 255))
    return im, base


def build_chikoo():
    """The palm squirrel: three parts is enough for a creature this size."""
    rig = Rig(root_pos=(0, 0))
    rig.tag = 'chikoo'
    body, body_piv = _draw_squirrel_body(); body = _volumize(body)
    head, head_piv = _draw_squirrel_head(); head = _volumize(head, volume=0.26)
    tail, tail_piv = _draw_squirrel_tail(); tail = _volumize(tail)
    rig.add(Part('tail', tail, tail_piv, 'body', (52, 140), z=5))
    rig.add(Part('body', body, body_piv, z=10))
    rig.add(Part('head', head, head_piv, 'body', (74, 46), z=20))
    return rig


def build_background(size=(1920, 1080)):
    """A simple lane: warm wall, ground, and soft depth."""
    w, h = size
    bg = Image.new('RGBA', size, (238, 226, 200, 255))
    d = ImageDraw.Draw(bg)
    for i in range(h):                                              # sky-to-wall wash
        f = i / h
        d.line([(0, i), (w, i)],
               fill=(int(236 - 26 * f), int(224 - 30 * f), int(198 - 34 * f), 255))
    d.rectangle((0, int(h * 0.78), w, h), fill=(196, 172, 138, 255))   # ground
    d.rectangle((0, int(h * 0.78), w, int(h * 0.79)), fill=(170, 146, 116, 255))
    for x in range(0, w, 260):                                      # wall panels
        d.rectangle((x + 8, int(h * 0.30), x + 244, int(h * 0.78)),
                    fill=(228, 214, 186, 255))
    bg = bg.filter(ImageFilter.GaussianBlur(3))                     # push it back
    return bg


# --------------------------------------------------------------------------
def call_out_pause():
    """Ten seconds of the beat that appears three times in every episode:
    settle, lift the lantern, tilt the head, hold three full seconds, wave.

    Angles were found by rendering a pose sheet rather than guessed. For the
    right arm, negative swings it outward and up; positive crosses it inward.
    The left arm mirrors that. Elbow bend does most of the readability work:
    a straight arm reads as pointing, a bent one as holding something up.
    """
    a = Animation()

    # Breathing runs the whole way through — nothing in a good shot is fully
    # still, and a held pose without it looks like a frozen frame.
    a.track('torso', 'dy', [(0, 0), (1.2, -7), (2.6, 0), (4.0, -7), (5.4, 0),
                            (6.8, -7), (8.2, 0), (9.6, -7), (10, -4)])
    a.track('torso', 'rot', [(0, -1.0), (2.5, 1.0), (5.0, -1.0), (7.5, 1.0), (10, -0.5)])

    # Head settles, then the questioning tilt lands with the lantern and holds
    a.track('head', 'rot', [(0, 0), (1.4, 2), (3.0, -4), (4.2, -10), (7.4, -10),
                            (8.0, -5), (9.2, -7), (10, -7)])

    # Braids lag behind the head — follow-through is what sells weight
    a.track('braid_l', 'rot', [(0, 3), (1.6, -2), (3.3, 5), (4.6, 10), (7.6, 8),
                               (8.3, 2), (9.5, 5), (10, 4)])
    a.track('braid_r', 'rot', [(0, -3), (1.7, 3), (3.4, -5), (4.7, -10), (7.7, -8),
                               (8.4, -1), (9.6, -4), (10, -3)])

    # The lift: upper arm swings out and up, elbow closes to bring the lantern
    # beside her face. Small overshoot so it settles instead of snapping.
    a.track('arm_r', 'rot', [(0, -6), (1.6, -6), (3.0, -58), (3.5, -54), (10, -54)],
            easing=ease_out_back)
    a.track('fore_r', 'rot', [(0, 5), (1.6, 5), (3.0, -115), (3.5, -108), (10, -108)],
            easing=ease_out_back)
    # The lantern hangs from a ring handle, so it stays upright in world space
    # while the arm rotates underneath it. These values cancel the arm chain.
    a.track('lantern', 'rot', [(0, 1), (1.6, 1), (3.0, 173), (3.5, 158),
                               (4.2, 164), (10, 162)])

    # Left arm rests through the pause, then waves once the lantern is settled
    a.track('arm_l', 'rot', [(0, 6), (1.6, 8), (4.2, 10), (7.4, 10),
                             (7.9, 118), (8.3, 104), (8.7, 122), (9.1, 106),
                             (9.5, 118), (10, 96)])
    a.track('fore_l', 'rot', [(0, 4), (1.6, 5), (4.2, 6), (7.4, 6),
                              (7.9, 44), (8.3, 18), (8.7, 46), (9.1, 20),
                              (9.5, 42), (10, 26)])

    # A small weight shift, not a walk
    a.track('leg_l', 'rot', [(0, 1.5), (2.5, -1.5), (5.0, 1.5), (7.5, -1.5), (10, 0)])
    a.track('leg_r', 'rot', [(0, -1.5), (2.5, 1.5), (5.0, -1.5), (7.5, 1.5), (10, 0)])
    return a


def walk_cycle(seconds=10.0, step=0.52):
    """A looping walk. The feet cycle in place and the world slides past.

    Timing is the whole game here. Each step is a contact (foot planted, body
    at its lowest), a passing position (body at its highest), then the next
    contact on the other foot. The body therefore bobs *twice* per full stride,
    not once — get that wrong and the walk reads as a limp.
    """
    a = Animation()
    n = int(seconds / step) + 2
    t = lambda i: i * step

    # Legs alternate. One is swinging forward while the other drives back.
    a.track('leg_l', 'rot', [(t(i), 20 if i % 2 == 0 else -20) for i in range(n)])
    a.track('leg_r', 'rot', [(t(i), -20 if i % 2 == 0 else 20) for i in range(n)])

    # The free arm counter-swings against the legs — opposite arm to opposite
    # leg, which is what stops a walk looking like a toy soldier. It needs a
    # wide swing to read at all; small angles just look like a twitch.
    a.track('arm_l', 'rot', [(t(i), -26 if i % 2 == 0 else 26) for i in range(n)])
    a.track('fore_l', 'rot', [(t(i), 8 if i % 2 == 0 else 22) for i in range(n)])

    # The lantern hand stays up at her side, so the lantern rides at hip height
    # instead of dragging along the ground. It swings a little, but far less
    # than the free arm — she is carrying something and knows it.
    a.track('arm_r', 'rot', [(t(i), -18 if i % 2 == 0 else -10) for i in range(n)])
    a.track('fore_r', 'rot', [(t(i), -58 if i % 2 == 0 else -50) for i in range(n)])

    # Body bob at twice the step rate: down on each contact, up on each pass
    bob = []
    for i in range(n * 2):
        bob.append((i * step / 2, 0 if i % 2 == 0 else -13))
    a.track('torso', 'dy', bob)
    a.track('torso', 'rot', [(t(i), 2.0 if i % 2 == 0 else -2.0) for i in range(n)])

    # Head stays level-ish — it counters the body, it does not ride it
    a.track('head', 'rot', [(t(i), -1.5 if i % 2 == 0 else 1.5) for i in range(n)])

    # Braids swing a half-beat behind the body. That lag is the follow-through.
    a.track('braid_l', 'rot', [(t(i) + step * 0.35, 12 if i % 2 == 0 else -8)
                               for i in range(n)])
    a.track('braid_r', 'rot', [(t(i) + step * 0.35, -8 if i % 2 == 0 else 12)
                               for i in range(n)])

    # The lantern hangs from its ring handle, so it stays upright in world
    # space while the arm swings underneath it, lagging half a beat behind.
    a.track('lantern', 'rot', [(t(i) + step * 0.5, 82 if i % 2 == 0 else 66)
                               for i in range(n)])
    return a


def scrolling_background(size=(1920, 1080), speed=210.0):
    """Returns a callable(t) that slides a tiled lane past the camera."""
    w, h = size
    tile = build_background((w * 2, h))
    def at(t):
        off = int((t * speed) % w)
        frame = Image.new('RGBA', size)
        frame.paste(tile.crop((off, 0, off + w, h)), (0, 0))
        return frame
    return at


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'tara_callout_test.mp4'
    which = sys.argv[2] if len(sys.argv) > 2 else 'callout'
    size = (1920, 1080)
    rig = build_rig(lit_points=3)
    print(f'rig: {len(rig.parts)} parts   animation: {which}')

    if which == 'walk':
        anim, bg = walk_cycle(10.0), scrolling_background(size)
    else:
        anim, bg = call_out_pause(), build_background(size)

    render_video(rig, anim, out, seconds=10.0, fps=24, size=size, background=bg)


if __name__ == '__main__':
    main()
