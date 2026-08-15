"""Objective QC for a rendered take.

Watching a filmstrip catches composition errors but not temporal ones -- a
one-frame pop or a foot that slides two pixels a frame is invisible in stills and
obvious in motion.  These metrics find them without playing anything back.

* **motion energy** -- mean |frame difference|.  Should be a smooth periodic
  curve for a walk cycle.
* **jerk** -- second difference of motion energy.  Isolated spikes are pops,
  usually a layer snapping or a curve with a discontinuity.
* **foot skate** -- the planted foot must travel at exactly the scroll speed.
  Any residual is the amount the shoe slides across the ground per frame.
"""

from __future__ import annotations

import glob
import os

import numpy as np
from PIL import Image
from scipy import ndimage


def load(frame_dir: str, stride: int = 1) -> np.ndarray:
    files = sorted(glob.glob(os.path.join(frame_dir, "*.png")))[::stride]
    return np.stack([np.asarray(Image.open(f).convert("RGB"), np.float32) / 255.0 for f in files])


def motion_energy(frames: np.ndarray) -> np.ndarray:
    return np.array([np.abs(frames[i] - frames[i - 1]).mean() for i in range(1, len(frames))])


def jerk(energy: np.ndarray) -> np.ndarray:
    return np.abs(np.diff(energy, 2)) if len(energy) > 2 else np.zeros(0)


def shoe_track(frames: np.ndarray) -> np.ndarray:
    """Centroid x of the red shoes, per frame.  Their colour is unique in shot."""
    out = np.zeros(len(frames))
    for i, f in enumerate(frames):
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        m = (r > 0.34) & (r > g * 1.7) & (r > b * 1.5) & (np.arange(f.shape[0])[:, None] > f.shape[0] * 0.6)
        m = ndimage.binary_opening(m, np.ones((3, 3)))
        out[i] = ndimage.center_of_mass(m)[1] if m.any() else np.nan
    return out


def report(frame_dir: str) -> dict:
    frames = load(frame_dir)
    e = motion_energy(frames)
    j = jerk(e)
    # A pop is a jerk far outside the normal spread of the take.
    thresh = j.mean() + 4.0 * j.std() if len(j) else 0.0
    pops = [int(i + 2) for i, v in enumerate(j) if v > thresh and v > 0.002]
    return {
        "frames": int(len(frames)),
        "motion_mean": float(e.mean()),
        "motion_min": float(e.min()),
        "motion_max": float(e.max()),
        # A ratio far above ~3 means the take stalls and lurches.
        "motion_ratio": float(e.max() / max(e.min(), 1e-6)),
        "jerk_mean": float(j.mean()) if len(j) else 0.0,
        "jerk_max": float(j.max()) if len(j) else 0.0,
        "pop_frames": pops,
        "black_frames": [int(i) for i, f in enumerate(frames) if f.mean() < 0.02],
    }


def contact_sheet(frame_dir: str, out_path: str, count: int = 9, cols: int = 3, cell=(426, 240)):
    files = sorted(glob.glob(os.path.join(frame_dir, "*.png")))
    idx = np.linspace(0, len(files) - 1, count).astype(int)
    rows = (count + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell[0], rows * cell[1]))
    for n, i in enumerate(idx):
        sheet.paste(Image.open(files[i]).resize(cell), ((n % cols) * cell[0], (n // cols) * cell[1]))
    sheet.save(out_path)
    return out_path
