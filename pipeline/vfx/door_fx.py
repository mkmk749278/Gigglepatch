#!/usr/bin/env python3
"""
Door VFX compositor — draws the animated magic door onto a photoreal alley plate.
Flux supplies the plate; the magic is composited here (plate + comp, like real VFX).
"""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 720
TEAL   = (30, 240, 215)
TEALHI = (170, 255, 245)
GOLD   = (255, 190, 95)

# Door geometry on the plate: centred, at the far end of the alley
DX, DY, DW, DH = 566, 250, 148, 300     # x, y, width, height
ARCH = 46                                # arched top rise


def door_outline_pts(n=240):
    """Points tracing the door outline, starting bottom-left, going up and around."""
    pts = []
    x0, x1 = DX, DX + DW
    y0, y1 = DY, DY + DH          # y0 = top (springline), y1 = floor
    # left jamb: bottom -> top
    for i in range(n // 4):
        t = i / (n // 4)
        pts.append((x0, y1 + (y0 - y1) * t))
    # arch: left -> right
    for i in range(n // 4):
        t = i / (n // 4)
        a = math.pi * t
        pts.append((x0 + DW * t, y0 - math.sin(a) * ARCH))
    # right jamb: top -> bottom
    for i in range(n // 4):
        t = i / (n // 4)
        pts.append((x1, y0 + (y1 - y0) * t))
    # threshold: right -> left
    for i in range(n // 4):
        t = i / (n // 4)
        pts.append((x1 - DW * t, y1))
    return pts

PTS = door_outline_pts()


def _screen(base, glow):
    b = np.asarray(base, dtype=np.float32) / 255
    g = np.asarray(glow, dtype=np.float32) / 255
    return Image.fromarray((((1 - (1 - b) * (1 - g))) * 255).clip(0, 255).astype(np.uint8))


def _bloom(layer, passes=((28, 1.0), (10, 0.8), (4, 0.6))):
    """Multi-pass gaussian bloom, summed."""
    acc = np.zeros((H, W, 3), dtype=np.float32)
    for radius, weight in passes:
        acc += np.asarray(layer.filter(ImageFilter.GaussianBlur(radius)),
                          dtype=np.float32) * weight
    return Image.fromarray(acc.clip(0, 255).astype(np.uint8))


def _spill(cx, cy, radius, color, strength):
    """Radial light spill onto the environment."""
    g = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(g)
    steps = 22
    for i in range(steps, 0, -1):
        f = i / steps
        r = int(radius * (1 - f) + 6)
        a = strength * (f ** 1.7)
        d.ellipse([cx - r, cy - r * 0.85, cx + r, cy + r * 0.85],
                  fill=tuple(int(c * a) for c in color))
    return g.filter(ImageFilter.GaussianBlur(radius / 5))


def trace_frame(plate, t):
    """t 0->1 : the teal line drawing the door outline."""
    n = max(2, int(t * len(PTS)))
    line = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(line)
    seg = PTS[:n]
    if len(seg) >= 2:
        d.line(seg, fill=TEAL, width=3)
        # bright leading spark
        tip = seg[-1]
        d.ellipse([tip[0] - 7, tip[1] - 7, tip[0] + 7, tip[1] + 7], fill=TEALHI)
    out = _screen(plate, _bloom(line))
    # faint ambient spill grows as the outline completes
    out = _screen(out, _spill(DX + DW // 2, DY + DH // 2, 220, TEAL, 0.10 + 0.22 * t))
    return out


def erupt_frame(plate, t):
    """t 0->1 : the door blazes to full power and opens."""
    # solid outline
    line = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(line)
    d.line(PTS + [PTS[0]], fill=TEALHI, width=int(3 + 5 * t))

    # interior fills with warm market light
    inner = Image.new('RGB', (W, H), (0, 0, 0))
    di = ImageDraw.Draw(inner)
    fill = min(1.0, t * 1.6)
    if fill > 0:
        poly = [(x, y) for (x, y) in PTS]
        c = tuple(int(v * fill) for v in GOLD)
        di.polygon(poly, fill=c)
        inner = inner.filter(ImageFilter.GaussianBlur(9))

    out = _screen(plate, _bloom(line, ((40, 1.0), (16, 0.9), (6, 0.7))))
    out = _screen(out, _bloom(inner, ((30, 0.9), (10, 0.7))))

    # big spill across the alley
    cx, cy = DX + DW // 2, DY + DH // 2
    out = _screen(out, _spill(cx, cy, 560, TEAL, 0.30 + 0.30 * t))
    out = _screen(out, _spill(cx, cy + 120, 420, GOLD, 0.16 * t))

    # impact whiteout on the first beats
    if t < 0.16:
        a = (1 - t / 0.16) * 0.62
        flash = Image.new('RGB', (W, H), TEALHI)
        out = Image.blend(out, flash, a)

    # light rays
    if t > 0.15:
        rays = Image.new('RGB', (W, H), (0, 0, 0))
        dr = ImageDraw.Draw(rays)
        for i in range(13):
            ang = -math.pi / 2 + (i - 6) * 0.20
            L = 700 * min(1.0, (t - 0.15) * 2.2)
            dr.line([(cx, cy), (cx + math.cos(ang) * L, cy + math.sin(ang) * L)],
                    fill=tuple(int(c * 0.34) for c in TEALHI), width=8)
        out = _screen(out, rays.filter(ImageFilter.GaussianBlur(26)))
    return out


def open_frame(plate, t):
    """Steady state: door open, warm light pouring out, gentle pulse."""
    pulse = 0.90 + 0.10 * math.sin(t * math.pi * 3)
    line = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(line)
    d.line(PTS + [PTS[0]], fill=TEALHI, width=7)

    inner = Image.new('RGB', (W, H), (0, 0, 0))
    di = ImageDraw.Draw(inner)
    di.polygon([(x, y) for (x, y) in PTS],
               fill=tuple(int(c * pulse) for c in GOLD))
    inner = inner.filter(ImageFilter.GaussianBlur(11))

    out = _screen(plate, _bloom(line, ((34, 1.0), (12, 0.8))))
    out = _screen(out, _bloom(inner, ((26, 0.95), (9, 0.7))))
    cx, cy = DX + DW // 2, DY + DH // 2
    out = _screen(out, _spill(cx, cy, 520, TEAL, 0.30 * pulse))
    out = _screen(out, _spill(cx, cy + 110, 430, GOLD, 0.22 * pulse))

    # drifting motes
    m = Image.new('RGB', (W, H), (0, 0, 0))
    dm = ImageDraw.Draw(m)
    rng = np.random.default_rng(5)
    for i in range(34):
        px = rng.uniform(DX - 40, DX + DW + 40)
        base_y = rng.uniform(DY, DY + DH)
        py = base_y - ((t * 90 + i * 19) % 190)
        r = rng.uniform(1.2, 3.0)
        dm.ellipse([px - r, py - r, px + r, py + r], fill=GOLD)
    out = _screen(out, m.filter(ImageFilter.GaussianBlur(3)))
    return out
