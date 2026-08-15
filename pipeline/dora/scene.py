"""Procedural night-market environment for the Dora shots.

Layers are generated wider than the frame and scrolled at different rates, which
is what sells depth in a side-on travelling shot: rooftops crawl, the lantern
string slides, the kerb races past.  Everything is built once as a tall RGBA
strip and sampled per frame, so per-frame cost is a couple of array copies.

Palette follows the series bible: deep violet starlit sky, warm amber lantern
light, teal accents.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SKY_TOP = (14, 10, 38)
SKY_LOW = (58, 26, 74)
HORIZON = (108, 52, 82)


def _blur(img: Image.Image, r: float) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(r))


def _haze(img: Image.Image, colour, amount: float) -> Image.Image:
    """Wash a layer toward an atmospheric colour -- distance, in one operation."""
    a = np.asarray(img, np.float32)
    tint = np.array(colour, np.float32)
    a[..., :3] += (tint - a[..., :3]) * amount
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def sky(w: int, h: int, rng: np.random.Generator) -> Image.Image:
    grad = np.zeros((h, w, 3), np.float32)
    t = (np.arange(h, dtype=np.float32) / (h - 1))[:, None]
    top = np.array(SKY_TOP, np.float32) / 255.0
    low = np.array(SKY_LOW, np.float32) / 255.0
    hor = np.array(HORIZON, np.float32) / 255.0
    # Two-stop ramp: night above, warm haze where the market glow hits the air.
    k = np.clip((t - 0.45) / 0.55, 0.0, 1.0)[..., None]
    ramp = top * (1 - t)[..., None] + low * t[..., None]
    ramp = ramp + (hor - ramp) * (k**2.2) * 0.55
    grad[:] = ramp
    img = Image.fromarray((np.clip(grad, 0, 1) * 255).astype(np.uint8))

    stars = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(stars)
    for _ in range(260):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.62)
        r = rng.uniform(0.4, 1.5)
        v = int(rng.uniform(70, 235) * (1.0 - y / (h * 0.75)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=max(v, 0))
    stars = _blur(stars, 0.5)
    out = np.asarray(img, np.float32) + np.asarray(stars, np.float32)[..., None] * 0.85
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def rooftops(w: int, h: int, rng: np.random.Generator, base: int, colour, window) -> Image.Image:
    """A silhouetted skyline band with a scatter of lit windows."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = -40
    while x < w + 40:
        bw = int(rng.uniform(46, 132))
        bh = int(rng.uniform(38, 150))
        top = base - bh
        d.rectangle([x, top, x + bw, h], fill=colour)
        if rng.random() < 0.55:  # a shallow pitched roof
            d.polygon([(x - 6, top), (x + bw + 6, top), (x + bw // 2, top - rng.uniform(12, 34))], fill=colour)
        for _ in range(int(rng.uniform(0, 5))):
            wx = x + rng.uniform(6, max(8, bw - 14))
            wy = top + rng.uniform(10, max(12, bh - 12))
            ww, wh = rng.uniform(5, 11), rng.uniform(6, 13)
            glow = int(rng.uniform(120, 255))
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=window + (glow,))
        x += bw + int(rng.uniform(2, 16))
    return img


def lantern_string(w: int, h: int, rng: np.random.Generator, y: int, sag: int) -> Image.Image:
    """Paper lanterns on a catenary -- the market's own light sources."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    span = 240
    for i in range(0, w + span, span):
        for k in range(0, span, 34):
            x = i + k
            if x > w:
                break
            f = (k / span) * 2 - 1
            ly = y + int(sag * (1 - f * f))
            d.line([(x - 34, y + int(sag * (1 - ((k - 34) / span * 2 - 1) ** 2))), (x, ly)],
                   fill=(90, 70, 96, 150), width=1)
            r = rng.uniform(5, 9)
            hues = [(255, 190, 96), (255, 148, 96), (255, 224, 150)]
            hue = hues[int(rng.integers(len(hues)))]
            d.ellipse([x - r, ly - r * 1.15, x + r, ly + r * 1.15], fill=hue + (255,))
    glow = _blur(img, 7)
    out = Image.alpha_composite(Image.new("RGBA", (w, h), (0, 0, 0, 0)), glow)
    return Image.alpha_composite(out, img)


def ground(w: int, h: int, rng: np.random.Generator) -> Image.Image:
    """Wet cobble strip, drawn in perspective.

    The first pass drew seams as full-width horizontal lines, which read as video
    banding rather than a street.  Cobbles are laid out in rows that get taller
    and wider toward camera, so the paving converges to the horizon and the
    surface has a direction.
    """
    img = np.zeros((h, w, 4), np.float32)
    t = (np.arange(h, dtype=np.float32) / max(h - 1, 1))[:, None]
    base = np.array([0.11, 0.08, 0.16], np.float32)
    far = np.array([0.21, 0.14, 0.23], np.float32)
    img[..., :3] = far * (1 - t)[..., None] + base * t[..., None]
    img[..., 3] = 1.0
    img[..., :3] += rng.normal(0.0, 0.020, (h, w, 1)).astype(np.float32)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(out)

    y = 2.0
    row = 0
    while y < h:
        depth = y / h  # 0 at the horizon, 1 at camera
        rh = 3.0 + 26.0 * depth**1.9
        cw = 16.0 + 92.0 * depth**1.7
        seam = int(20 + 40 * depth)
        d.line([(0, y), (w, y)], fill=(196, 168, 190, seam), width=1)
        x = -cw * (0.5 if row % 2 else 0.0)
        while x < w:
            d.line([(x, y), (x, y + rh)], fill=(186, 160, 184, int(seam * 0.72)), width=1)
            x += cw
        y += rh
        row += 1
    return out


class Backdrop:
    """All parallax layers, pre-rendered and ready to be sampled per frame."""

    def __init__(self, w: int, h: int, span: int = 3, seed: int = 11):
        rng = np.random.default_rng(seed)
        self.w, self.h = w, h
        W = w * span
        self.span = span
        horizon = int(h * 0.72)

        self.horizon = horizon
        far = rooftops(W, h, rng, horizon - 26, (26, 18, 52, 255), (255, 196, 120))
        mid = rooftops(W, h, rng, horizon - 4, (18, 12, 38, 255), (255, 172, 96))
        # Aerial perspective: the distant row is hazed and softened toward the
        # sky colour so the skyline has depth instead of stacking as flat cutouts.
        far = _haze(_blur(far, 1.6), (72, 44, 92), 0.42)
        mid = _haze(mid, (54, 32, 74), 0.18)

        self.layers: list[tuple[float, Image.Image, int]] = []
        self.layers.append((0.06, sky(W, h, rng).convert("RGBA"), 0))
        self.layers.append((0.22, far, 0))
        self.layers.append((0.42, mid, 0))
        self.layers.append((0.55, lantern_string(W, h, rng, int(h * 0.16), 34), 0))
        self.layers.append((1.0, ground(W, h - horizon, rng), horizon))
        yy = np.arange(h, dtype=np.float32)[:, None, None]
        band = np.exp(-(((yy - horizon) / 46.0) ** 2))
        self._fog = band * np.array([0.085, 0.055, 0.105], np.float32)
        # Focus sits on the character's feet; everything behind falls off.
        self._dof = np.clip(1.0 - (yy - horizon) / float(h - horizon), 0.0, 1.0) ** 1.4

        self._cache: dict[int, np.ndarray] = {}
        # Foreground bokeh, defocused and drifting faster than the ground.
        fg = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(fg)
        for _ in range(70):
            x, y = rng.uniform(0, W), rng.uniform(h * 0.25, h)
            r = rng.uniform(6, 20)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 200, 130, int(rng.uniform(18, 52))))
        self.fg = _blur(fg, 9)

    def frame(self, scroll: float) -> np.ndarray:
        """Composite the backdrop at `scroll` px of camera travel.

        Cached on the rounded scroll: motion-blur sub-frames land on nearly the
        same backdrop, and rebuilding it (five composites plus a defocus blur)
        for each of them was most of the render time.
        """
        key = int(round(scroll))
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        out = self._compose(scroll)
        if len(self._cache) > 8:
            self._cache.clear()
        self._cache[key] = out
        return out

    def _compose(self, scroll: float) -> np.ndarray:
        out = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 255))
        for factor, layer, top in self.layers:
            off = int(scroll * factor) % (layer.width - self.w - 1)
            crop = layer.crop((off, 0, off + self.w, min(layer.height, self.h)))
            box = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            box.paste(crop, (0, top))
            out = Image.alpha_composite(out, box)

        img = np.asarray(out, np.float32)[..., :3] / 255.0
        # Ground fog: hides the hard join between skyline and street, and gives
        # the far end of the lane somewhere to disappear into.
        img = img + self._fog
        # Defocus: sharp at the kerb by camera, soft toward the horizon.
        soft = np.asarray(_blur(Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)), 2.4),
                          np.float32) / 255.0
        return img * (1 - self._dof) + soft * self._dof

    def foreground(self, scroll: float) -> np.ndarray:
        off = int(scroll * 1.45) % (self.fg.width - self.w - 1)
        crop = self.fg.crop((off, 0, off + self.w, self.h))
        return np.asarray(crop, np.float32) / 255.0
