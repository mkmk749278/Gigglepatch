"""Cut a row of items on a magenta screen into separate transparent PNGs.

Two of the model-sheet panels arrive as a horizontal strip of small objects —
the six mouth shapes, and the lantern at each stage of THE STAR COUNT. They need
no silhouette analysis, only separating and keying, so they get their own tool
rather than being forced through the rig cutter.

    python3 tools/cut_strip.py mouths.jpeg parts/ mouth 6
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autorig import load_rgba          # noqa: E402  (path set above)


def columns(alpha, min_gap=6, min_width=8):
    """Split on vertical bands that are entirely transparent."""
    filled = (alpha > 24).any(axis=0)
    spans, start = [], None
    for x, on in enumerate(filled):
        if on and start is None:
            start = x
        elif not on and start is not None:
            spans.append((start, x - 1))
            start = None
    if start is not None:
        spans.append((start, len(filled) - 1))

    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] <= min_gap:
            merged[-1] = (merged[-1][0], s[1])
        else:
            merged.append(s)
    return [s for s in merged if s[1] - s[0] >= min_width]


def cut_strip(path, out_dir, name, expect=None, pad=4):
    im = load_rgba(path, key='chroma', keep_largest=False)
    a = np.asarray(im)[..., 3]
    spans = columns(a)
    if expect and len(spans) != expect:
        print(f'  warning: found {len(spans)} items, expected {expect}')

    os.makedirs(out_dir, exist_ok=True)
    made = []
    for i, (x0, x1) in enumerate(spans):
        col = a[:, x0:x1 + 1]
        ys = np.flatnonzero((col > 24).any(axis=1))
        box = (max(x0 - pad, 0), max(int(ys[0]) - pad, 0),
               min(x1 + 1 + pad, im.width), min(int(ys[-1]) + 1 + pad, im.height))
        piece = im.crop(box)
        f = os.path.join(out_dir, f'{name}_{i}.png')
        piece.save(f)
        made.append((f, piece.size))
    return made


if __name__ == '__main__':
    src, dst, nm = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else None
    for f, size in cut_strip(src, dst, nm, n):
        print(f'  {os.path.basename(f):16s} {size[0]:4d}x{size[1]}')
