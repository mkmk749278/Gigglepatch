"""Chroma key for the Dora plate pack.

The plates are rendered on a magenta backdrop that is *not* flat -- it carries a
vignette and a light gradient, so a flat colour-distance key tears.  Keying on
chromaticity (rgb normalised by its own max) throws luminance away, so the
vignette stops mattering and only the hue/purity of the pixel is judged.

Why chromaticity and not hue: black hair sits at chroma (1,1,1) and white
leggings sit at chroma (1,1,1) too -- both are far from the backdrop's
(1.0, 0.22, 0.97), so they survive.  A naive "green channel is low => background"
test kills black hair, which is most of this character's silhouette.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, grey_erosion

BG_CHROMA = np.array([1.0, 0.22, 0.97], dtype=np.float32)

# The generator stamps a white four-point sparkle in the bottom-right corner.
# It is white, so the key keeps it -- cut it explicitly.
WATERMARK_BOX = (1230, 610, 1376, 768)


def chromaticity(rgb: np.ndarray) -> np.ndarray:
    """rgb float [0,1] -> unit-max chromaticity, luminance removed."""
    mx = rgb.max(axis=2, keepdims=True)
    return rgb / np.maximum(mx, 1e-4)


def key_plate(
    path: str,
    t_in: float = 0.16,
    t_out: float = 0.42,
    edge_shrink: float = 1.1,
    despill_strength: float = 0.9,
) -> Image.Image:
    """Return an RGBA cutout of one plate.

    t_in/t_out are chromaticity distances: below t_in is certainly backdrop,
    above t_out is certainly subject, between them the matte ramps smoothly so
    hair wisps keep soft edges instead of stair-stepping.
    """
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    dist = np.linalg.norm(chromaticity(rgb) - BG_CHROMA, axis=2)

    # Very dark pixels have unstable chromaticity (noise dominates), but they are
    # never backdrop here -- the backdrop is bright.  Protect them.
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    dist = np.maximum(dist, np.clip((0.30 - luma) * 4.0, 0.0, 1.0))

    alpha = np.clip((dist - t_in) / (t_out - t_in), 0.0, 1.0)
    alpha = alpha * alpha * (3.0 - 2.0 * alpha)  # smoothstep

    # JPEG chroma subsampling leaves a 1-2px magenta halo. Shrink then soften:
    # erosion pulls the matte inside the fringe, the blur puts the softness back.
    alpha = grey_erosion(alpha, size=3)
    alpha = gaussian_filter(alpha, edge_shrink)
    alpha = np.clip((alpha - 0.06) / 0.94, 0.0, 1.0)

    x0, y0, x1, y1 = WATERMARK_BOX
    alpha[y0:y1, x0:x1] = 0.0

    out = despill(rgb, alpha, despill_strength)

    rgba = np.dstack([out, alpha]).clip(0.0, 1.0)
    return Image.fromarray((rgba * 255.0 + 0.5).astype(np.uint8), "RGBA")


def despill(rgb: np.ndarray, alpha: np.ndarray, strength: float) -> np.ndarray:
    """Remove magenta bounce from subject pixels.

    Magenta spill shows up as red and blue both exceeding green.  Clamp them
    toward green, but only by `strength` and only where it actually happens, so
    the red shoes and the skin tones (legitimately red-dominant) are left alone
    -- those are protected by restricting the correction to the edge band.
    """
    out = rgb.copy()
    r, g, b = out[..., 0], out[..., 1], out[..., 2]

    # Edge band: pixels near the matte boundary, where spill lives.
    band = gaussian_filter(alpha, 3.0)
    band = np.clip(1.0 - np.abs(band * 2.0 - 1.0), 0.0, 1.0) * (alpha > 0.02)

    cap = np.maximum(g, (r + b) * 0.5 * 0.55 + g * 0.45)
    spill = np.minimum(r, b) - cap
    amount = np.clip(spill, 0.0, None) * strength * band
    out[..., 0] = r - amount
    out[..., 2] = b - amount
    return out


def trim(img: Image.Image, pad: int = 2) -> tuple[Image.Image, tuple[int, int]]:
    """Crop to the alpha bounding box; returns the crop and its origin."""
    a = np.asarray(img)[..., 3]
    ys, xs = np.where(a > 6)
    if len(xs) == 0:
        return img, (0, 0)
    x0, x1 = max(0, xs.min() - pad), min(img.width, xs.max() + 1 + pad)
    y0, y1 = max(0, ys.min() - pad), min(img.height, ys.max() + 1 + pad)
    return img.crop((x0, y0, x1, y1)), (x0, y0)
