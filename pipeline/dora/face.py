"""Eyelids for the head layer.

The plate has open eyes and nothing else, so a blink has to be manufactured.
Compressing the eye vertically is the obvious move and it looks wrong -- a real
eyelid does not squash the eye, it *covers* it.  So the eye is left exactly where
it is and a strip of lid skin from just above it is stretched down over the top,
with a lash line at the leading edge and a little contact shadow under it.

Boxes are in plate coordinates of pose_walking.png.
"""

from __future__ import annotations

import numpy as np

# (x0, x1, y0, y1) per eye -- lids, white and pupil, not just the iris.
EYES = [(245, 296, 95, 143), (313, 356, 91, 137)]
LID_SOURCE = 11  # px of skin above the eye that becomes the closing lid
LASH = np.array([0.22, 0.13, 0.12], np.float32)


def blink(head: np.ndarray, amount: float, eyes=EYES) -> np.ndarray:
    """Return a copy of the head layer with the lids `amount` (0..1) closed."""
    if amount <= 0.004:
        return head
    out = head.copy()
    a = float(np.clip(amount, 0.0, 1.0))
    for x0, x1, y0, y1 in eyes:
        h = y1 - y0
        cut = max(1, int(round(a * h * 0.94)))
        # Stretch the lid strip [y0-LID_SOURCE, y0) across [y0, y0+cut).
        src_rows = y0 - LID_SOURCE + (np.arange(cut) / cut) * LID_SOURCE
        src = np.clip(np.round(src_rows).astype(int), 0, head.shape[0] - 1)
        out[y0 : y0 + cut, x0:x1] = head[src, x0:x1]

        edge = y0 + cut
        if edge + 3 < head.shape[0]:
            # Lash line, then a soft shadow the lid casts on the eye below it.
            lid = out[edge - 1 : edge + 1, x0:x1]
            alpha = lid[..., 3:4]
            lid[..., :3] = lid[..., :3] * 0.35 + LASH * alpha * 0.65
            shade = out[edge + 1 : edge + 5, x0:x1]
            fall = np.linspace(0.72, 1.0, shade.shape[0], dtype=np.float32)[:, None, None]
            shade[..., :3] *= fall
    return out
