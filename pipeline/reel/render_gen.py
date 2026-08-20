#!/usr/bin/env python3
"""
Animate the generated plates into shot segments.

Uses a lighter grade than the Blender path: these plates already carry their
own atmospheric perspective and depth of field, so adding more fog just mutes
them. Drifting light motes are layered on top so a shot has motion of its own
and does not read as a photograph being panned across.
"""
import os, sys, time, math
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, comp, shots as SH

import numpy as np
from PIL import Image
import imageio_ffmpeg

OUT_W, OUT_H = 1280, 720
PLATES = 'plates_gen'


def ease_io(x):
    return x * x * (3 - 2 * x)


def load_scaled(name):
    d = os.path.join(env.SP, PLATES)
    rgb = Image.open(os.path.join(d, f'{name}.png')).convert('RGB')
    dep = Image.open(os.path.join(d, f'{name}_depth_0001.png'))
    rgb = rgb.resize((OUT_W, OUT_H), Image.LANCZOS)
    dep = dep.resize((OUT_W, OUT_H), Image.BILINEAR)
    return (np.asarray(rgb, np.float32) / 255.0,
            np.asarray(dep, np.float32) / 65535.0)


class Motes:
    """Slow drifting specks of light, scaled by depth so they sit in the scene."""

    def __init__(self, n, w, h, seed):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, w, n)
        self.y = r.uniform(0, h, n)
        self.z = r.uniform(0.05, 0.85, n)        # near motes drift further
        self.vx = r.uniform(-7, 7, n)
        self.vy = r.uniform(-11, -3, n)
        self.ph = r.uniform(0, 6.28, n)
        self.sz = r.uniform(1.0, 2.6, n)
        self.w, self.h = w, h

    def draw(self, canvas, t, depth, gain=0.55):
        disp = 1.0 / (self.z * 6.0 + 0.35)
        x = (self.x + self.vx * t * disp) % self.w
        y = (self.y + self.vy * t * disp) % self.h
        twinkle = 0.45 + 0.55 * np.sin(self.ph + t * 1.7)
        xi, yi = x.astype(np.int32), y.astype(np.int32)
        # only keep motes that sit in front of the scene at that pixel
        vis = depth[np.clip(yi, 0, self.h - 1), np.clip(xi, 0, self.w - 1)] > self.z
        amp = twinkle * vis * gain
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                fall = 1.0 if (dx == 0 and dy == 0) else 0.34
                xs = np.clip(xi + dx, 0, self.w - 1)
                ys = np.clip(yi + dy, 0, self.h - 1)
                a = (amp * fall * self.sz / 2.6)[:, None] * np.array([1.0, 0.86, 0.62])
                np.add.at(canvas, (ys, xs), a)
        return canvas


def render_shot(shot):
    name, _set, _loc, _look, _lens, secs, move = shot
    d = os.path.join(env.SP, PLATES)
    if not os.path.exists(os.path.join(d, f'{name}.png')):
        return name, 0, 'MISSING PLATE'

    out = os.path.join(env.SP, 'segments_gen', f'{name}.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rgb, depth = load_scaled(name)
    rig = comp.ParallaxRig(rgb, depth)
    n = int(secs * SH.FPS)
    dx, dy, zoom_end = move
    seed = abs(hash(name)) % (2 ** 31)
    rng = np.random.default_rng(seed)
    motes = Motes(190, OUT_W, OUT_H, seed)

    wr = imageio_ffmpeg.write_frames(out, (OUT_W, OUT_H), fps=SH.FPS, quality=8,
                                     macro_block_size=1, ffmpeg_log_level='error')
    wr.send(None)
    t0 = time.time()
    for i in range(n):
        u = ease_io(i / max(1, n - 1))
        t = i / SH.FPS
        f = rig.frame(dx=dx * (u - 0.5), dy=dy * (u - 0.5),
                      zoom=1.0 + (zoom_end - 1.0) * u)
        f = comp.dof(f, depth, focus=0.42 + 0.08 * math.sin(u * math.pi),
                     strength=2.0)
        f = motes.draw(f, t, depth)
        f = comp.bloom(f, thresh=0.68, radius=22, gain=0.50)
        f = comp.grade(f, lift=(0.004, 0.007, 0.014), gain=(1.04, 1.00, 0.99),
                       gamma=0.98, sat=1.14)
        f = comp.vignette(f, amount=0.22)
        f = comp.grain(f, amount=0.008, rng=rng)
        if i < 12:
            f *= (i + 1) / 13.0
        elif i >= n - 12:
            f *= (n - i) / 13.0
        wr.send(comp.to_u8(f))
    wr.close()
    return name, n, f'{(time.time()-t0)/n*1000:.0f} ms/frame'


def main():
    print(f'{len(SH.SHOTS)} shots, {SH.TOTAL_SECONDS*SH.FPS} frames', flush=True)
    t0 = time.time()
    with Pool(processes=int(os.environ.get('REEL_WORKERS', 4))) as pool:
        for name, n, msg in pool.imap_unordered(render_shot, SH.SHOTS):
            print(f'  {name:14s} {n:5d} frames  {msg}', flush=True)
    print(f'\nALL SEGMENTS DONE in {(time.time()-t0)/60:.1f} min')


if __name__ == '__main__':
    main()
