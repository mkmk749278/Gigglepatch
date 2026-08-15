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
    w = h = 200
    im = _img(w, h)
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(10):                                             # five-point star
        ang = -math.pi / 2 + i * math.pi / 5
        r = 78 if i % 2 == 0 else 32
        pts.append((100 + r * math.cos(ang), 104 + r * math.sin(ang)))
    d.polygon(pts, fill=BRASS)
    d.line([(100, 26), (100, 8)], fill=BRASS, width=7)              # ring handle
    d.ellipse((86, 0, 114, 22), outline=BRASS, width=7)
    for i in range(5):                                              # the five lights
        ang = -math.pi / 2 + i * 2 * math.pi / 5
        cx, cy = 100 + 52 * math.cos(ang), 104 + 52 * math.sin(ang)
        on = i < lit_points
        d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11),
                  fill=GLOW if on else BRASS_LT)
    return im, (100, 8)


# --------------------------------------------------------------------------
def build_rig(lit_points=0):
    """Assemble the hierarchy. Rotate the torso and everything above follows."""
    # 560 puts the full figure in frame with headroom; 700 cropped the feet
    rig = Rig(root_pos=(960, 560))

    torso_img, torso_piv = _draw_torso()
    head_img, head_piv = _draw_head()
    bl_img, bl_piv = _draw_braid()
    br_img, br_piv = _draw_braid(flip=True)
    ua_img, ua_piv = _draw_arm(upper=True)
    fa_img, fa_piv = _draw_arm(upper=False)
    leg_img, leg_piv = _draw_leg()
    lan_img, lan_piv = _draw_lantern(lit_points)

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


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'tara_callout_test.mp4'
    size = (1920, 1080)
    rig = build_rig(lit_points=3)
    bg = build_background(size)
    print(f'rig: {len(rig.parts)} parts')
    render_video(rig, call_out_pause(), out, seconds=10.0, fps=24,
                 size=size, background=bg)


if __name__ == '__main__':
    main()
