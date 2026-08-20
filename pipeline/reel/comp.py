#!/usr/bin/env python3
"""
Numpy/PIL compositor.

Rendering every frame in Cycles costs ~17 h for five minutes. Instead each shot
is one rendered plate (colour + depth) that this module animates: depth-layered
parallax gives real camera movement from a still, and fog / bloom / DOF / grade
are all driven off the same depth pass. Cost is ~0.2 s/frame per worker.
"""
import numpy as np
from PIL import Image, ImageFilter


# ---------- io ----------

def load_plate(path_rgb, path_depth):
    rgb = np.asarray(Image.open(path_rgb).convert('RGB'), np.float32) / 255.0
    d = np.asarray(Image.open(path_depth), np.float32)
    d = d / 65535.0 if d.dtype == np.uint16 or d.max() > 255 else d / 255.0
    if d.shape != rgb.shape[:2]:
        d = np.asarray(Image.fromarray((d * 255).astype(np.uint8))
                       .resize((rgb.shape[1], rgb.shape[0]), Image.BILINEAR),
                       np.float32) / 255.0
    return rgb, d


def to_u8(rgb):
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def _blur(a, r):
    """Gaussian blur on an HxWx3 float array via PIL (fast C path)."""
    if r <= 0:
        return a
    im = Image.fromarray(to_u8(a))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


# ---------- camera ----------

class ParallaxRig:
    """
    Pre-decomposed depth layers for one shot.

    The depth pass is constant across a shot, so layer decomposition happens
    once here and each frame is just a gather. Layers are cropped to their
    bounding box: a depth slice usually covers a small part of frame, and
    warping the full canvas for each one was the single largest cost.
    """

    def __init__(self, rgb, depth, layers=10):
        self.rgb, self.depth = rgb, depth
        h, w = depth.shape
        self.h, self.w = h, w
        self.fill = _blur(rgb, 12)

        edges = np.linspace(0.0, 1.0, layers + 1)
        self.layers = []
        for i in range(layers - 1, -1, -1):          # far -> near
            lo, hi = edges[i], edges[i + 1]
            m = (depth >= lo) & (depth < hi)
            if not m.any():
                continue
            ys, xs = np.where(m)
            y0, y1 = int(ys.min()), int(ys.max()) + 1
            x0, x1 = int(xs.min()), int(xs.max()) + 1
            sub = m[y0:y1, x0:x1].astype(np.float32)
            mid = (lo + hi) * 0.5
            self.layers.append(dict(
                rgb=rgb[y0:y1, x0:x1] * sub[..., None], alpha=sub,
                box=(x0, y0, x1, y1), disp=1.0 / (mid * 6.0 + 0.35)))

    def frame(self, dx=0.0, dy=0.0, zoom=1.0):
        h, w = self.h, self.w
        out = np.zeros_like(self.rgb)
        acc = np.zeros((h, w), np.float32)
        cx, cy = w * 0.5, h * 0.5

        for L in self.layers:
            x0, y0, x1, y1 = L['box']
            sx, sy = dx * L['disp'], dy * L['disp']
            sc = 1.0 + (zoom - 1.0) * L['disp']

            # where this source box lands on the destination canvas
            dx0 = int(np.floor((x0 - cx + sx) * sc + cx))
            dx1 = int(np.ceil((x1 - cx + sx) * sc + cx))
            dy0 = int(np.floor((y0 - cy + sy) * sc + cy))
            dy1 = int(np.ceil((y1 - cy + sy) * sc + cy))
            dx0, dy0 = max(dx0, 0), max(dy0, 0)
            dx1, dy1 = min(dx1, w), min(dy1, h)
            if dx1 <= dx0 or dy1 <= dy0:
                continue

            yy, xx = np.mgrid[dy0:dy1, dx0:dx1].astype(np.float32)
            u = (xx - cx) / sc + cx - sx - x0
            v = (yy - cy) / sc + cy - sy - y0
            sh, sw = L['alpha'].shape
            inside = (u >= 0) & (u <= sw - 1) & (v >= 0) & (v <= sh - 1)
            ui = np.clip(u, 0, sw - 1).astype(np.int32)
            vi = np.clip(v, 0, sh - 1).astype(np.int32)

            alp = L['alpha'][vi, ui] * inside
            wgt = alp * (1.0 - acc[dy0:dy1, dx0:dx1])
            out[dy0:dy1, dx0:dx1] += L['rgb'][vi, ui] * wgt[..., None]
            acc[dy0:dy1, dx0:dx1] += wgt

        hole = 1.0 - acc
        if hole.max() > 0.01:
            out += self.fill * hole[..., None]
        return out


# ---------- look ----------

def fog(rgb, depth, color=(0.06, 0.09, 0.20), density=1.25, power=1.5):
    """Atmospheric perspective. The single biggest depth cue in a flat render."""
    f = np.clip(depth, 0, 1) ** power
    f = 1.0 - np.exp(-density * f * 2.2)
    return rgb * (1 - f[..., None]) + np.array(color, np.float32) * f[..., None]


def bloom(rgb, thresh=0.62, radius=26, gain=0.75, tint=(1.0, 0.80, 0.55)):
    """
    Light bleed from the lanterns -- the warmth in the frame.

    Glow is inherently low-frequency, so it is built at quarter resolution and
    scaled back up. Same result, a quarter of the blur cost.
    """
    h, w = rgb.shape[:2]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    m = np.clip((lum - thresh) / max(1e-3, 1 - thresh), 0, 1)
    bright = rgb * m[..., None]

    small = Image.fromarray(to_u8(bright)).resize((w // 4, h // 4), Image.BILINEAR)
    g1 = small.filter(ImageFilter.GaussianBlur(radius / 4))
    g2 = small.filter(ImageFilter.GaussianBlur(radius / 4 * 2.4))
    glow = (np.asarray(g1.resize((w, h), Image.BILINEAR), np.float32) +
            0.6 * np.asarray(g2.resize((w, h), Image.BILINEAR), np.float32)) / 255.0
    return np.clip(rgb + glow * np.array(tint, np.float32) * gain, 0, 4)


def dof(rgb, depth, focus=0.35, strength=6.0, falloff=1.6):
    """Two-tap depth-of-field: sharp plate blended toward a blurred copy."""
    coc = np.clip(np.abs(depth - focus) * falloff, 0, 1)
    return rgb * (1 - coc[..., None]) + _blur(rgb, strength) * coc[..., None]


def grade(rgb, lift=(0.010, 0.016, 0.030), gain=(1.06, 1.00, 0.96),
          gamma=0.96, sat=1.12):
    x = np.clip(rgb, 0, 4)
    x = x * np.array(gain, np.float32) + np.array(lift, np.float32)
    x = np.clip(x, 0, 4) ** gamma
    lum = (x @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    return np.clip(lum + (x - lum) * sat, 0, 1)


def vignette(rgb, amount=0.34, softness=1.5):
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx / w - .5) * 2) ** 2 + ((yy / h - .5) * 2) ** 2) / 1.4142
    return rgb * (1.0 - amount * np.clip(r, 0, 1) ** softness)[..., None]


def grain(rgb, amount=0.012, rng=None):
    rng = rng or np.random
    return np.clip(rgb + rng.normal(0, amount, rgb.shape).astype(np.float32), 0, 1)


def letterbox(rgb, ratio=2.39):
    h, w = rgb.shape[:2]
    bar = int(max(0, (h - w / ratio) / 2))
    if bar > 0:
        rgb = rgb.copy()
        rgb[:bar], rgb[h - bar:] = 0, 0
    return rgb
