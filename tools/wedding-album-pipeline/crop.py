"""Intelligent reframing.

Chooses a crop window for a target aspect ratio using face geometry plus a
gradient-energy saliency proxy, with rule-of-thirds eye-line placement. Only
ever *removes* pixels — never stretches, never extends the frame, never
synthesises missing anatomy. If the required crop would discard too much of the
subject, the caller is told the crop is not viable and keeps the original
orientation.
"""
from __future__ import annotations

import cv2
import numpy as np

# A portrait crop out of a landscape frame is only allowed if it keeps at least
# this fraction of the original frame area, and all detected faces survive.
MIN_AREA_KEEP = 0.34


def energy_map(rgb: np.ndarray, short: int = 256) -> np.ndarray:
    """Cheap saliency proxy: blurred gradient magnitude, contrast-normalised."""
    h, w = rgb.shape[:2]
    s = short / min(h, w)
    small = cv2.resize(rgb, (max(16, int(w * s)), max(16, int(h * s))), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    e = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 3.0)
    # saturation adds weight: decorated/clothed subjects beat blank walls
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    e = e / max(e.max(), 1e-6) + 0.45 * (hsv[..., 1].astype(np.float32) / 255.0)
    return e


def _face_anchor(faces: list, W: int, H: int):
    """Weighted centre of interest and eye-line from face boxes (largest wins)."""
    if not faces:
        return None
    ws = [f[2] * f[3] for f in faces]
    tot = float(sum(ws)) or 1.0
    cx = sum((f[0] + f[2] / 2) * w for f, w in zip(faces, ws)) / tot
    cy = sum((f[1] + f[3] / 2) * w for f, w in zip(faces, ws)) / tot
    big = max(faces, key=lambda f: f[2] * f[3])
    eye_y = big[1] + big[3] * 0.42
    return cx, cy, eye_y, big


def smart_crop_box(rgb: np.ndarray, target_aspect: float, faces: list | None = None,
                   thirds: bool = True):
    """Return (x0, y0, x1, y1) for the best crop at `target_aspect` (w/h).

    Strategy: take the largest window of the target aspect that fits, then slide
    it to maximise a score combining saliency mass, face containment and
    rule-of-thirds eye-line placement.
    """
    H, W = rgb.shape[:2]
    src_aspect = W / H
    if target_aspect >= src_aspect:      # limited by width -> crop height
        cw = W
        ch = int(round(W / target_aspect))
    else:                                # limited by height -> crop width
        ch = H
        cw = int(round(H * target_aspect))
    cw, ch = min(cw, W), min(ch, H)

    e = energy_map(rgb)
    eh, ew = e.shape
    sx, sy = ew / W, eh / H
    integral = cv2.integral(e)

    def energy_in(x0, y0):
        X0, Y0 = int(x0 * sx), int(y0 * sy)
        X1, Y1 = int(min(ew, (x0 + cw) * sx)), int(min(eh, (y0 + ch) * sy))
        if X1 <= X0 or Y1 <= Y0:
            return 0.0
        return float(integral[Y1, X1] - integral[Y0, X1] - integral[Y1, X0] + integral[Y0, X0])

    anchor = _face_anchor(faces or [], W, H)
    total_e = energy_in(0, 0) if (cw == W and ch == H) else None

    xs = range(0, max(1, W - cw + 1), max(1, (W - cw) // 24 or 1)) if W > cw else [0]
    ys = range(0, max(1, H - ch + 1), max(1, (H - ch) // 24 or 1)) if H > ch else [0]

    best, best_s = (0, 0), -1e18
    for y0 in ys:
        for x0 in xs:
            s = energy_in(x0, y0) / max(cw * ch, 1)
            if anchor:
                cx, cy, eye_y, big = anchor
                # all faces must stay fully inside, else heavy penalty
                inside = all(x0 <= f[0] and f[0] + f[2] <= x0 + cw and
                             y0 <= f[1] and f[1] + f[3] <= y0 + ch for f in faces)
                if not inside:
                    s -= 4.0
                # centre of interest near horizontal centre of the crop
                s -= 1.6 * abs(((cx - x0) / cw) - 0.5) ** 2
                if thirds:
                    # eye line towards the upper third
                    s -= 2.2 * abs(((eye_y - y0) / ch) - 0.36) ** 2
                else:
                    s -= 1.2 * abs(((cy - y0) / ch) - 0.5) ** 2
            if s > best_s:
                best_s, best = s, (x0, y0)
    x0, y0 = best
    return int(x0), int(y0), int(x0 + cw), int(y0 + ch)


def portrait_crop_viable(rgb: np.ndarray, target_aspect: float, faces: list | None):
    """Is a portrait recompose defensible for this frame?

    Requires: enough area retained, and every detected face fully preserved.
    """
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = smart_crop_box(rgb, target_aspect, faces)
    keep = ((x1 - x0) * (y1 - y0)) / float(W * H)
    ok_faces = True
    if faces:
        ok_faces = all(x0 <= f[0] and f[0] + f[2] <= x1 and y0 <= f[1] and f[1] + f[3] <= y1
                       for f in faces)
    return (keep >= MIN_AREA_KEEP and ok_faces), (x0, y0, x1, y1), round(keep, 4)


def crop_to_aspect(img: np.ndarray, target_aspect: float, faces: list | None = None,
                   thirds: bool = True) -> np.ndarray:
    x0, y0, x1, y1 = smart_crop_box(img, target_aspect, faces, thirds)
    return img[y0:y1, x0:x1]


def fit_cover(img: np.ndarray, box_w: int, box_h: int, faces: list | None = None,
              thirds: bool = True) -> np.ndarray:
    """Crop to the box aspect (content-aware), then resample to exact size.

    Downscaling uses INTER_AREA; the rare upscale uses Lanczos4. Never stretches:
    aspect is always corrected by cropping, not by non-uniform scaling.
    """
    c = crop_to_aspect(img, box_w / box_h, faces, thirds)
    interp = cv2.INTER_AREA if (c.shape[1] >= box_w) else cv2.INTER_LANCZOS4
    return cv2.resize(c, (box_w, box_h), interpolation=interp)


def scale_faces(faces: list, sx: float, sy: float) -> list:
    return [[int(f[0] * sx), int(f[1] * sy), int(f[2] * sx), int(f[3] * sy)] for f in faces]
