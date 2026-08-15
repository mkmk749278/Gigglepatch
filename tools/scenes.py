"""The world of the series, drawn as layered stage art.

Backgrounds are built at stage resolution (larger than the output frame) so the
camera has room to pan and push in without upscaling. Each location is a set of
flat layers — sky, far, mid, ground — which is exactly how a cut-out show is
built, and it means a shot can be re-framed without redrawing anything.

Palette and locations come from series-tara/CHARACTER_BIBLE.md.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

STAGE = (2560, 1440)

# Time of day, per the character bible's three-point lighting scheme
MORNING = dict(sky=(250, 232, 196), haze=(252, 238, 206), ground=(198, 172, 132),
               wall=(240, 228, 202), warm=(255, 226, 168), shade=(176, 152, 120))
MIDDAY = dict(sky=(226, 236, 246), haze=(242, 246, 250), ground=(206, 186, 152),
              wall=(246, 244, 236), warm=(255, 250, 236), shade=(168, 158, 140))
SUNSET = dict(sky=(252, 206, 154), haze=(250, 214, 172), ground=(178, 140, 104),
              wall=(242, 206, 168), warm=(255, 198, 132), shade=(140, 108, 92))

GREEN = (96, 148, 86)
GREEN_D = (68, 116, 64)
GREEN_L = (132, 176, 100)
TRUNK = (108, 84, 62)
TRUNK_D = (84, 64, 48)


def _stage(size=STAGE):
    return Image.new('RGBA', size, (0, 0, 0, 0))


def _sky(size, pal):
    """Vertical wash, warm at the horizon."""
    w, h = size
    img = Image.new('RGBA', (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        f = (y / h) ** 0.8
        rgb = tuple(int(a + (b - a) * f) for a, b in zip(pal['sky'], pal['haze']))
        d.point((0, y), fill=rgb + (255,))
    return img.resize(size, Image.BILINEAR)


def _leaf_cluster(d, cx, cy, r, seed, dark=False):
    rng = random.Random(seed)
    col = GREEN_D if dark else GREEN
    for _ in range(14):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0, r * 0.7)
        s = rng.uniform(r * 0.35, r * 0.62)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.7
        d.ellipse((x - s, y - s * 0.78, x + s, y + s * 0.78),
                  fill=col if rng.random() > 0.35 else GREEN_L)


def _wall(d, x0, y0, x1, y1, pal, panels=True):
    d.rectangle((x0, y0, x1, y1), fill=pal['wall'])
    d.rectangle((x0, y0, x1, y0 + 14), fill=pal['shade'])
    if panels:
        for x in range(int(x0) + 90, int(x1), 300):
            d.line([(x, y0 + 20), (x, y1)], fill=pal['shade'], width=3)


# --------------------------------------------------------------------------
# locations
# --------------------------------------------------------------------------
def neem_lane(pal=MORNING, size=STAGE):
    """A narrow lane between compound walls, neem branches overhead.

    Drawn in one-point perspective toward a vanishing point rather than as flat
    elevation. Without the convergence it reads as a wall, not a lane you could
    walk down.
    """
    w, h = size
    img = _sky(size, pal)
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.56)
    vx = int(w * 0.5)

    # lane floor: a trapezoid narrowing to the vanishing point
    d.polygon([(-w * 0.5, h), (w * 1.5, h),
               (vx + w * 0.06, horizon), (vx - w * 0.06, horizon)],
              fill=pal['ground'])

    for side in (-1, 1):                                   # the two walls
        near_x = vx + side * w * 0.62
        far_x = vx + side * w * 0.06
        d.polygon([(near_x, h * 0.02), (near_x, h),
                   (far_x, horizon), (far_x, horizon - h * 0.20)],
                  fill=pal['wall'])
        d.polygon([(near_x, h * 0.02), (far_x, horizon - h * 0.20),
                   (far_x, horizon - h * 0.24), (near_x, h * -0.03)],
                  fill=pal['shade'])
        for k in range(1, 7):                              # receding panel lines
            f = k / 7.0
            px = near_x + (far_x - near_x) * f
            top = h * 0.02 + (horizon - h * 0.20 - h * 0.02) * f
            bot = h + (horizon - h) * f
            d.line([(px, top), (px, bot)], fill=pal['shade'], width=max(1, int(4 * (1 - f))))

    for k in range(7):                                     # rangoli, receding
        f = k / 7.0
        y = h - (h - horizon) * f * 0.92
        rw = 60 * (1 - f * 0.8)
        d.ellipse((vx - rw, y - rw * 0.45, vx + rw, y + rw * 0.45),
                  outline=(250, 248, 242, 170), width=max(2, int(5 * (1 - f))))

    d.rectangle((vx - w * 0.055, horizon - h * 0.10, vx - w * 0.040, horizon),
                fill=(120, 128, 132))                      # hand pump
    for i in range(8):                                     # canopy overhead
        _leaf_cluster(d, i * 360 - 40, 30 + (i % 3) * 40, 200, seed=i,
                      dark=(i % 2 == 0))
    return img


def mango_grove(pal=MORNING, size=STAGE):
    """Rows of old mango trees, dappled light, fruit in the canopy."""
    w, h = size
    img = _sky(size, pal)
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.74)

    far = Image.new('RGBA', size, (0, 0, 0, 0))                   # distant trees
    fd = ImageDraw.Draw(far)
    for i in range(9):
        _leaf_cluster(fd, 90 + i * 300, horizon - 190, 150, seed=100 + i, dark=True)
    far = far.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(far)

    d.rectangle((0, horizon, w, h), fill=(150, 168, 108))         # grass
    d.rectangle((0, horizon, w, horizon + 10), fill=GREEN_D)

    for i, x in enumerate((300, 1050, 1900, 2400)):               # trunks
        d.rectangle((x - 34, int(h * 0.20), x + 34, horizon + 20), fill=TRUNK)
        d.rectangle((x + 12, int(h * 0.20), x + 34, horizon + 20), fill=TRUNK_D)
        _leaf_cluster(d, x, int(h * 0.17), 260, seed=20 + i)
    for i in range(11):                                           # mangoes
        rng = random.Random(70 + i)
        mx = rng.randint(180, w - 180)
        my = rng.randint(int(h * 0.10), int(h * 0.30))
        d.ellipse((mx - 22, my - 26, mx + 22, my + 26), fill=(238, 178, 58))
    for i in range(16):                                           # fallen fruit
        rng = random.Random(200 + i)
        fx, fy = rng.randint(60, w - 60), rng.randint(horizon + 40, h - 40)
        d.ellipse((fx - 15, fy - 12, fx + 15, fy + 12), fill=(226, 170, 62))
    return img


def banyan_court(pal=MORNING, size=STAGE):
    """The hub: an enormous banyan, aerial roots, a stone platform.

    The roots hang *from the canopy* and stop above the ground, with varying
    length and a slight curve. Drawn floor-to-ceiling and evenly spaced they
    read as a fence.
    """
    w, h = size
    img = _sky(size, pal)
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.76)
    d.rectangle((0, horizon, w, h), fill=pal['ground'])
    d.rectangle((0, horizon, w, horizon + 9), fill=pal['shade'])

    cx = int(w * 0.52)
    d.polygon([(cx - 120, int(h * 0.12)), (cx + 120, int(h * 0.12)),
               (cx + 190, horizon + 10), (cx - 190, horizon + 10)], fill=TRUNK)
    d.polygon([(cx + 40, int(h * 0.12)), (cx + 120, int(h * 0.12)),
               (cx + 190, horizon + 10), (cx + 70, horizon + 10)], fill=TRUNK_D)

    rng = random.Random(5)
    for i in range(16):                                    # hanging aerial roots
        rx = 90 + i * 165 + rng.randint(-40, 40)
        if abs(rx - cx) < 150:
            continue
        top = int(h * 0.20) + rng.randint(-30, 40)
        drop = rng.uniform(0.34, 0.78)
        bottom = top + (horizon - top) * drop
        bend = rng.randint(-22, 22)
        d.line([(rx, top), (rx + bend * 0.5, (top + bottom) / 2), (rx + bend, bottom)],
               fill=TRUNK_D, width=rng.choice((7, 9, 12)), joint='curve')

    for i in range(10):                                    # canopy
        _leaf_cluster(d, 120 + i * 280, 50 + (i % 4) * 44, 240, seed=40 + i,
                      dark=(i % 3 == 0))

    d.ellipse((cx - 430, horizon - 30, cx + 430, horizon + 96),
              fill=(196, 188, 174))                        # stone platform
    d.ellipse((cx - 430, horizon - 44, cx + 430, horizon + 74), fill=(224, 218, 204))
    return img


def courtyard(pal=MORNING, size=STAGE):
    """The Blue Door House: lime-washed walls, indigo door, tulsi pot."""
    w, h = size
    img = _sky(size, pal)
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.72)

    _wall(d, -20, int(h * 0.12), w + 20, horizon, pal, panels=False)
    d.rectangle((0, int(h * 0.12), w, int(h * 0.155)), fill=pal['shade'])

    dx = int(w * 0.34)                                            # the blue door
    d.rectangle((dx, int(h * 0.30), dx + 300, horizon), fill=(46, 62, 138))
    d.rectangle((dx + 12, int(h * 0.32), dx + 140, horizon - 14), fill=(58, 76, 158))
    d.rectangle((dx + 158, int(h * 0.32), dx + 288, horizon - 14), fill=(58, 76, 158))
    d.ellipse((dx + 132, int(h * 0.52), dx + 168, int(h * 0.55)), fill=(214, 176, 96))

    for wx in (int(w * 0.70), int(w * 0.86)):                     # windows
        d.rectangle((wx, int(h * 0.34), wx + 170, int(h * 0.52)), fill=(120, 150, 140))
        d.rectangle((wx, int(h * 0.34), wx + 170, int(h * 0.52)),
                    outline=(70, 96, 92), width=8)

    d.rectangle((0, horizon, w, h), fill=pal['ground'])            # swept ground
    d.rectangle((0, horizon, w, horizon + 8), fill=pal['shade'])

    tx = int(w * 0.13)                                             # tulsi pot
    d.polygon([(tx - 66, horizon + 150), (tx + 66, horizon + 150),
               (tx + 48, horizon + 8), (tx - 48, horizon + 8)], fill=(178, 96, 62))
    d.rectangle((tx - 74, horizon - 12, tx + 74, horizon + 16), fill=(196, 112, 72))
    _leaf_cluster(d, tx, horizon - 78, 78, seed=9)
    return img


LOCATIONS = {
    'neem_lane': neem_lane,
    'mango_grove': mango_grove,
    'banyan_court': banyan_court,
    'courtyard': courtyard,
}


def ground_shadow(frame, x, y, rx, ry=None, alpha=58):
    """A soft ellipse under a character. Without it figures look pasted on."""
    ry = ry or rx * 0.30
    layer = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((x - rx, y - ry, x + rx, y + ry),
                                  fill=(40, 30, 24, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(rx * 0.16))
    frame.alpha_composite(layer)
    return frame


def scroller(builder, pal=MORNING, size=STAGE, speed=210.0):
    """Slide a location past the camera for walking shots."""
    tile = builder(pal, (size[0] * 2, size[1]))
    def at(t):
        off = int((t * speed) % size[0])
        out = Image.new('RGBA', size)
        out.paste(tile.crop((off, 0, off + size[0], size[1])), (0, 0))
        return out
    return at
