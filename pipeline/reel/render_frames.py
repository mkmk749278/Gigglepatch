#!/usr/bin/env python3
"""
Animate every shot's plate into a video segment.

Shots are independent, so they parallelise cleanly: each worker takes one shot,
animates it, and writes its own segment. The assembler concatenates them. That
avoids both a shared frame counter and millions of loose PNGs on disk.
"""
import os, sys, time, math
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, comp, shots as SH

import numpy as np
import imageio_ffmpeg


def ease_io(x):
    """Smooth acceleration and deceleration -- nothing moves at constant speed."""
    return x * x * (3 - 2 * x)


def plate_paths(name):
    d = os.path.join(env.SP, 'plates')
    rgb = os.path.join(d, f'{name}.png')
    depth = os.path.join(d, f'{name}_depth_0001.png')
    return rgb, depth


def render_shot(shot):
    name, set_name, loc, look, lens, secs, move = shot
    rgb_p, depth_p = plate_paths(name)
    if not (os.path.exists(rgb_p) and os.path.exists(depth_p)):
        return name, 0, 'MISSING PLATE'

    out = os.path.join(env.SP, 'segments', f'{name}.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rgb, depth = comp.load_plate(rgb_p, depth_p)
    rig = comp.ParallaxRig(rgb, depth)
    h, w = depth.shape
    n = int(secs * SH.FPS)
    dx, dy, zoom_end = move
    rng = np.random.default_rng(abs(hash(name)) % (2 ** 31))

    wr = imageio_ffmpeg.write_frames(
        out, (w, h), fps=SH.FPS, quality=8, macro_block_size=1,
        ffmpeg_log_level='error')
    wr.send(None)

    t0 = time.time()
    for i in range(n):
        u = ease_io(i / max(1, n - 1))
        # camera drifts from -half to +half of the move so the plate's framing
        # stays roughly centred over the shot
        f = rig.frame(dx=dx * (u - 0.5), dy=dy * (u - 0.5),
                      zoom=1.0 + (zoom_end - 1.0) * u)
        f = comp.fog(f, depth)
        f = comp.dof(f, depth, focus=0.40 + 0.10 * math.sin(u * math.pi),
                     strength=5.0)
        f = comp.bloom(f)
        f = comp.grade(f)
        f = comp.vignette(f)
        f = comp.grain(f, rng=rng)
        # 12-frame dip from/to black at the head and tail of every shot
        if i < 12:
            f *= (i + 1) / 13.0
        elif i >= n - 12:
            f *= (n - i) / 13.0
        wr.send(comp.to_u8(f))
    wr.close()
    return name, n, f'{(time.time()-t0)/n*1000:.0f} ms/frame'


def main():
    todo = [s for s in SH.SHOTS]
    print(f'{len(todo)} shots, {SH.TOTAL_SECONDS*SH.FPS} frames total', flush=True)
    t0 = time.time()
    with Pool(processes=int(os.environ.get('REEL_WORKERS', 4))) as pool:
        for name, n, msg in pool.imap_unordered(render_shot, todo):
            print(f'  {name:14s} {n:5d} frames  {msg}', flush=True)
    print(f'\nALL SEGMENTS DONE in {(time.time()-t0)/60:.1f} min')


if __name__ == '__main__':
    main()
