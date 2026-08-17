"""Cinematic colour / enhancement engine.

Conventional (non-generative) retouching only: every operation is a tone, colour
or spatial transform of the real pixels. Nothing is synthesised, no identity is
altered. Tone work happens in LINEAR light; contrast/grade in perceptual sRGB.

Parameters are derived per image from its own measured statistics, so the grade
adapts to each lighting environment instead of stamping one LUT on everything.
"""
from __future__ import annotations

import cv2
import numpy as np

# Reference noise levels calibrated from the measured flat-tile residual
# distribution of THIS collection (s02): min 0.38 / p25 1.35 / med 2.06 /
# p75 2.78 / max 7.65. The whole set was shot at ISO 200-250, so the residual is
# dominated by JPEG texture and fine fabric detail rather than sensor noise.
# REF is therefore set at the median: the typical frame receives NO denoising,
# and only the genuinely noisy tail is touched.
NOISE_REF = 2.20
NOISE_MAX = 5.50

# ---------------------------------------------------------------- colour space


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def luma(rgb: np.ndarray) -> np.ndarray:
    """Rec.709 luminance of a linear-light RGB image."""
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


# ---------------------------------------------------------------- white balance


def estimate_wb_gains(srgb: np.ndarray, strength: float = 0.40,
                      max_dev: float = 0.07) -> np.ndarray:
    """Neutral-reference white balance.

    Grey-world fails badly on this collection: the frames are dominated by warm
    content (gold, red silk, skin, terracotta), so averaging the whole frame
    reads the *subject* as a colour cast and over-corrects towards cyan —
    turning gilded mandap decor teal and rotating a pink saree to violet.

    Instead the illuminant is estimated only from genuinely near-neutral pixels
    (white dhotis, painted walls, backdrops, paving). If the frame contains no
    reliable neutral, white balance is left alone rather than guessed. Gains are
    additionally clamped to +/-`max_dev` and scaled by `strength`, so ambient
    warmth is retained as character.
    """
    f = np.clip(srgb, 0, 1).astype(np.float32)
    hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
    sat, val = hsv[..., 1], hsv[..., 2]
    neutral = (sat < 0.18) & (val > 0.32) & (val < 0.97)
    if neutral.sum() < max(500, 0.004 * sat.size):
        return np.ones(3, np.float32)          # no trustworthy reference
    lin = srgb_to_linear(f)
    est = np.array([lin[..., c][neutral].mean() for c in range(3)], np.float32)
    est = np.maximum(est, 1e-6)
    gains = est.mean() / est
    gains = 1.0 + (gains - 1.0) * strength
    return np.clip(gains, 1.0 - max_dev, 1.0 + max_dev).astype(np.float32)


# ---------------------------------------------------------------- masks


def skin_mask(srgb: np.ndarray, faces: list | None = None) -> np.ndarray:
    """Soft 0..1 skin probability. Broad YCrCb+HSV gate, then blurred.

    Face boxes, when present, bias the mask so background objects of a similar
    hue (wood, brick, terracotta) are weighted down.
    """
    u8 = (np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    ycrcb = cv2.cvtColor(u8, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    cr, cb = ycrcb[..., 1].astype(np.int16), ycrcb[..., 2].astype(np.int16)
    h, s, v = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    m = ((cr >= 132) & (cr <= 180) & (cb >= 76) & (cb <= 128) &
         (v > 40) & (s > 22) & (s < 190) & ((h <= 28) | (h >= 172)))
    m = m.astype(np.float32)
    if faces:
        H, W = m.shape
        bias = np.full((H, W), 0.35, np.float32)
        for x, y, w, hh in faces:
            x0, y0 = max(0, int(x - 0.35 * w)), max(0, int(y - 0.45 * hh))
            x1, y1 = min(W, int(x + 1.35 * w)), min(H, int(y + 1.9 * hh))
            if x1 > x0 and y1 > y0:
                bias[y0:y1, x0:x1] = 1.0
        m *= bias
    k = max(3, (min(m.shape) // 200) | 1)
    return np.clip(cv2.GaussianBlur(m, (k, k), 0), 0, 1)


def edge_mask(srgb: np.ndarray) -> np.ndarray:
    """0..1 detail mask used to keep sharpening off flat areas (sky, walls, skin)."""
    g = cv2.cvtColor((np.clip(srgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    mag /= max(mag.max(), 1e-6)
    return np.clip(cv2.GaussianBlur(mag, (0, 0), 1.2) * 3.0, 0, 1)


# ---------------------------------------------------------------- tone (linear)


def apply_exposure(lin: np.ndarray, stops: float) -> np.ndarray:
    return lin * (2.0 ** stops)


def highlight_rolloff(lin: np.ndarray, knee: float = 0.72, strength: float = 1.0) -> np.ndarray:
    """Filmic compression above `knee` — recovers glare on white dhotis / walls
    without the grey HDR look. Applied on luminance so hue is preserved."""
    if strength <= 0:
        return lin
    y = luma(lin)
    over = np.maximum(y - knee, 0.0)
    # asymptotic soft clip: knee + (1-knee)*tanh(over/(1-knee))
    head = max(1e-3, 1.0 - knee)
    y_new = np.where(y > knee, knee + head * np.tanh(over / head), y)
    y_new = y + (y_new - y) * strength
    scale = np.where(y > 1e-6, y_new / np.maximum(y, 1e-6), 1.0)
    return lin * scale[..., None]


def shadow_lift(lin: np.ndarray, amount: float = 0.18, pivot: float = 0.16) -> np.ndarray:
    """Lift only the darkest region, tapering to zero by `pivot` — opens up
    shaded faces and dark interiors while keeping blacks from going milky."""
    if amount <= 0:
        return lin
    y = luma(lin)
    w = np.clip(1.0 - y / max(pivot, 1e-6), 0.0, 1.0) ** 1.5
    gain = 1.0 + amount * w
    return lin * gain[..., None]


def local_contrast(srgb: np.ndarray, amount: float = 0.16, radius_frac: float = 0.02) -> np.ndarray:
    """Gentle large-radius unsharp on luminance = dimensional depth, not HDR."""
    if amount <= 0:
        return srgb
    lab = cv2.cvtColor((np.clip(srgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
    L = lab[..., 0].astype(np.float32)
    r = max(3, int(min(srgb.shape[:2]) * radius_frac) | 1)
    blur = cv2.GaussianBlur(L, (0, 0), r / 3.0)
    L2 = np.clip(L + (L - blur) * amount, 0, 255)
    lab[..., 0] = L2.astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0


def s_curve(srgb: np.ndarray, strength: float = 0.16, pivot: float = 0.46) -> np.ndarray:
    """Smooth contrast S-curve in perceptual space, applied via a LUT."""
    if strength <= 0:
        return srgb
    x = np.linspace(0, 1, 1024, dtype=np.float32)
    # blend identity with a smoothstep remap -> monotonic S, endpoints fixed
    smooth = x * x * (3 - 2 * x)
    curve = (1 - strength) * x + strength * smooth
    # re-anchor the pivot so overall brightness does not drift, tapering the
    # correction to zero at both ends to keep the curve monotonic
    shift = float(np.interp(pivot, x, curve) - pivot)
    curve = np.clip(curve - shift * (1.0 - np.abs(2 * x - 1) ** 2), 0, 1)
    curve = np.maximum.accumulate(curve)
    out = np.empty_like(srgb)
    for c in range(3):
        out[..., c] = np.interp(srgb[..., c], x, curve)
    return out


# ---------------------------------------------------------------- colour grade


def selective_saturation(srgb: np.ndarray, global_amt: float = 1.06,
                         skin: np.ndarray | None = None, skin_amt: float = 1.0,
                         red_guard: float = 0.55) -> np.ndarray:
    """Saturation with two protections:

    * skin is held near its original saturation (no orange faces)
    * already-saturated reds are *not* pushed further, because the saree /
      kumkum reds in this set sit right at the top of the gamut and would
      posterise. `red_guard` scales down the boost as red saturation rises.
    """
    hsv = cv2.cvtColor(np.clip(srgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    amt = np.full_like(s, global_amt, dtype=np.float32)
    if skin is not None:
        amt = amt * (1 - skin) + skin_amt * skin
    # reds: hue near 0 or 360 in OpenCV float HSV (degrees)
    red = np.clip(1.0 - np.minimum(np.abs(h - 0), np.abs(h - 360)) / 28.0, 0, 1)
    red_hot = red * np.clip((s - 0.55) / 0.45, 0, 1)
    amt = amt * (1 - red_hot * red_guard) + 1.0 * (red_hot * red_guard)
    hsv[..., 1] = np.clip(s * amt, 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def split_tone(srgb: np.ndarray, warm: float = 0.020, cool: float = 0.014) -> np.ndarray:
    """Very subtle warm highlights / cool shadows — the shared 'film' signature.
    Deliberately small so it reads as a look, not a colour cast."""
    y = cv2.cvtColor(np.clip(srgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2GRAY)
    hi = np.clip((y - 0.55) / 0.45, 0, 1)[..., None]
    lo = np.clip((0.42 - y) / 0.42, 0, 1)[..., None]
    out = srgb.copy()
    out += hi * np.array([warm, warm * 0.45, -warm * 0.55], np.float32)
    out += lo * np.array([-cool * 0.5, -cool * 0.1, cool], np.float32)
    return np.clip(out, 0, 1)


def gamut_guard(srgb: np.ndarray, thresh: float = 0.996, amount: float = 0.20) -> np.ndarray:
    """Very light touch on channels right at the ceiling.

    Deliberately weak: a fuchsia saree or kumkum red that was already clipped in
    camera is the real colour of the garment, and pulling it toward grey reads as
    a hue change (pink drifting to mauve). The guard only takes the hard edge off
    the very top of the channel rather than desaturating the fabric.
    """
    mx = srgb.max(axis=2)
    over = np.clip((mx - thresh) / max(1e-6, 1.0 - thresh), 0, 1)
    if over.max() <= 0:
        return srgb
    g = cv2.cvtColor(np.clip(srgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2GRAY)[..., None]
    w = (over * amount)[..., None]
    return np.clip(srgb * (1 - w) + g * w, 0, 1)


# ---------------------------------------------------------------- spatial


def denoise(srgb: np.ndarray, noise_level: float, skin: np.ndarray | None = None) -> np.ndarray:
    """Chroma-weighted denoise scaled to the measured noise. Luma detail is
    largely preserved so skin texture and fabric weave survive."""
    if noise_level <= NOISE_REF * 1.15:
        return srgb                     # already clean: do not touch texture
    excess = (noise_level - NOISE_REF) / max(NOISE_MAX - NOISE_REF, 1e-6)
    h_col = float(np.clip(2.0 + excess * 7.0, 2.0, 9.0))
    u8 = (np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    out = cv2.fastNlMeansDenoisingColored(u8, None, 2, h_col, 7, 21).astype(np.float32) / 255.0
    if skin is not None:  # a touch more smoothing on skin, still texture-safe
        w = (skin * 0.35)[..., None]
        out = out * (1 - w) + cv2.bilateralFilter(out, 7, 0.06, 9) * w
    return out


def sharpen(srgb: np.ndarray, amount: float = 0.55, radius: float = 1.1,
            detail: np.ndarray | None = None, skin: np.ndarray | None = None) -> np.ndarray:
    """Edge-masked unsharp. Skin is sharpened at reduced strength so pores and
    fabric stay natural and no halos appear along faces."""
    if amount <= 0:
        return srgb
    blur = cv2.GaussianBlur(srgb, (0, 0), radius)
    high = srgb - blur
    w = np.ones(srgb.shape[:2], np.float32)
    if detail is not None:
        w *= (0.35 + 0.65 * detail)
    if skin is not None:
        w *= (1.0 - 0.55 * skin)
    return np.clip(srgb + high * (amount * w[..., None]), 0, 1)


# ---------------------------------------------------------------- driver


def auto_params(tech: dict, profile: str = "default") -> dict:
    """Derive per-image correction amounts from that image's own measurements."""
    ml = tech.get("mean_luma", 0.45) or 0.45
    p = tech.get("percentiles") or [0, 10, 60, 110, 160, 220, 250]
    p1, p50, p99 = p[0] / 255.0, p[3] / 255.0, p[6] / 255.0
    clip_hi = tech.get("clip_high", 0.0) or 0.0
    noise = tech.get("noise", 1.0) or 1.0
    colorf = tech.get("colorfulness", 30.0) or 30.0
    contrast = (tech.get("contrast_std", 50.0) or 50.0) / 255.0

    # Exposure: preserve the photograph's own key. Only correct when the median
    # falls outside a comfortable band, and then only far enough to reach the
    # band edge -- a legitimately high-key studio frame must stay high-key, and
    # a candlelit interior must not be dragged up to mid-grey.
    lo, hi = 0.34, 0.60
    if p50 < lo:
        stops = float(np.log2(lo / max(p50, 0.02)))
    elif p50 > hi:
        stops = float(np.log2(hi / p50))
    else:
        stops = 0.0
    stops = float(np.clip(stops, -0.40, 0.90))
    # if highlights are already clipping, refuse to push exposure up
    if clip_hi > 0.02:
        stops = min(stops, 0.0)
    if clip_hi > 0.08:
        stops = min(stops, -0.18)

    shadows = float(np.clip(0.30 * (0.12 - p1) / 0.12, 0.0, 0.34)) + (0.10 if ml < 0.32 else 0.0)
    s_amt = float(np.clip(0.20 - (contrast - 0.20) * 0.55, 0.05, 0.24))
    # gentle boost, backed off on frames that are already highly colourful
    sat = float(np.clip(1.10 - max(0.0, colorf - 40.0) / 300.0, 1.00, 1.10))
    sharp = float(np.clip(0.62 - max(0.0, noise - NOISE_REF) * 0.16, 0.30, 0.66))
    lc = 0.16

    if profile == "hero":
        lc += 0.04
        s_amt += 0.02
    elif profile == "detail":
        sharp += 0.06
    return {"stops": round(stops, 3), "shadows": round(shadows, 3),
            "s_curve": round(s_amt, 3),
            "saturation": round(sat, 3), "sharpen": round(sharp, 3),
            "local_contrast": round(lc, 3), "noise": round(float(noise), 3)}


def grade(rgb_u8: np.ndarray, tech: dict, faces: list | None = None,
          profile: str = "default", params: dict | None = None):
    """Full grade. Input/output are uint8 RGB; internals are float32."""
    prm = params or auto_params(tech, profile)
    srgb = rgb_u8.astype(np.float32) / 255.0

    # 1. white balance (in linear light)
    gains = estimate_wb_gains(srgb)
    lin = srgb_to_linear(srgb) * gains[None, None, :]

    # 2. exposure -> highlights -> shadows, all linear.
    # Highlight rolloff is decided AFTER exposure, from the actual post-exposure
    # highlight population, not from the un-adjusted measurement.
    lin = apply_exposure(lin, prm["stops"])
    y = luma(lin)
    hot = float((y > 0.94).mean())
    hl = float(np.clip(hot * 14.0, 0.0, 1.0))
    lin = highlight_rolloff(lin, knee=0.72, strength=hl)
    lin = shadow_lift(lin, amount=prm["shadows"])
    out = np.clip(linear_to_srgb(lin), 0, 1)
    prm = {**prm, "highlight_strength": round(hl, 3)}

    # 3. masks computed once on the tone-corrected image
    sk = skin_mask(out, faces)
    det = edge_mask(out)

    # 4. perceptual contrast + depth
    out = s_curve(out, strength=prm["s_curve"])
    out = local_contrast(out, amount=prm["local_contrast"])

    # 5. colour
    out = selective_saturation(out, global_amt=prm["saturation"], skin=sk, skin_amt=1.02)
    out = split_tone(out)
    out = gamut_guard(out)

    # 6. spatial
    out = denoise(out, prm["noise"], skin=sk)
    out = sharpen(out, amount=prm["sharpen"], detail=det, skin=sk)

    return (np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8), prm, gains
