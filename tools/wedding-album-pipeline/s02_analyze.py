"""STAGE 3-4: TECHNICAL QUALITY ANALYSIS (OpenCV) + PERCEPTUAL HASHING (imagehash).

Single pixel-decode pass per image (half-scale DCT decode). Produces multiple
independent metrics rather than one score, plus Haar face geometry used later
for close-up detection and portrait-crop decisions.
Writes analysis/photo_technical.json
"""
import json
import os
import sys
import warnings
from multiprocessing import Pool
from pathlib import Path

# Pin BLAS/OpenMP/tflite thread pools to 1 *before* importing cv2/mediapipe.
# With 4 process workers, letting each spawn its own pool oversubscribes the box.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "TFLITE_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import cv2

cv2.setNumThreads(1)
import imagehash
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from config import ANALYSIS, ANALYSIS_LONG_EDGE

warnings.filterwarnings("ignore")
Image.MAX_IMAGE_PIXELS = None

CASCADE_F = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
CASCADE_P = cv2.data.haarcascades + "haarcascade_profileface.xml"
BLAZE = str(Path(__file__).parent.parent / "models" / "blaze_face_short_range.tflite")
_casc = {}
_blaze = {}


def cascades():
    if not _casc:
        _casc["f"] = cv2.CascadeClassifier(CASCADE_F)
        _casc["p"] = cv2.CascadeClassifier(CASCADE_P)
    return _casc["f"], _casc["p"]


def blaze():
    """mediapipe BlazeFace (short-range): high-precision boxes for large/near faces.
    Used for close-up detection and portrait-crop centring."""
    if "d" not in _blaze:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mpp
            from mediapipe.tasks.python import vision
            _blaze["mp"] = mp
            _blaze["d"] = vision.FaceDetector.create_from_options(
                vision.FaceDetectorOptions(
                    base_options=mpp.BaseOptions(model_asset_path=BLAZE),
                    min_detection_confidence=0.45))
        except Exception:  # noqa: BLE001
            _blaze["d"] = None
    return _blaze.get("d"), _blaze.get("mp")


BLAZE_EDGE = 768  # BlazeFace resizes to 128px internally; feeding it full res is waste


def blaze_faces(rgb):
    """Returns boxes in the coordinate space of `rgb`."""
    det, mp = blaze()
    if det is None:
        return []
    H, W = rgb.shape[:2]
    s = min(1.0, BLAZE_EDGE / max(W, H))
    src = (cv2.resize(rgb, (max(1, int(W * s)), max(1, int(H * s))),
                      interpolation=cv2.INTER_AREA) if s < 1.0 else rgb)
    try:
        res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                  data=np.ascontiguousarray(src)))
    except Exception:  # noqa: BLE001
        return []
    inv_s = 1.0 / s if s > 0 else 1.0
    out = []
    for d in res.detections:
        bb = d.bounding_box
        out.append({"box": [int(bb.origin_x * inv_s), int(bb.origin_y * inv_s),
                            int(bb.width * inv_s), int(bb.height * inv_s)],
                    "score": round(float(d.categories[0].score), 3),
                    "keypoints": [[round(k.x, 5), round(k.y, 5)] for k in (d.keypoints or [])]})
    return out


def load_half(path):
    """Fast half-scale decode, EXIF-rotated to display orientation."""
    im = Image.open(path)
    im.draft("RGB", (ANALYSIS_LONG_EDGE, ANALYSIS_LONG_EDGE))
    im = ImageOps.exif_transpose(im).convert("RGB")
    return np.asarray(im)


def sharpness_metrics(gray):
    """Laplacian variance globally and over the sharpest tile (handles shallow DOF)."""
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    glob = float(lap.var())
    h, w = gray.shape
    th, tw = h // 4, w // 4
    tiles = [float(lap[y:y + th, x:x + tw].var())
             for y in range(0, h - th + 1, th) for x in range(0, w - tw + 1, tw)]
    tiles.sort(reverse=True)
    best = float(np.mean(tiles[:2])) if tiles else glob
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    tenengrad = float(np.mean(gx * gx + gy * gy))
    return glob, best, tenengrad


def noise_estimate(gray):
    """Residual std after median filtering, measured in the flattest tiles only."""
    med = cv2.medianBlur(gray, 3)
    res = gray.astype(np.float32) - med.astype(np.float32)
    h, w = res.shape
    th, tw = h // 8, w // 8
    stats = []
    for y in range(0, h - th + 1, th):
        for x in range(0, w - tw + 1, tw):
            t = gray[y:y + th, x:x + tw]
            stats.append((float(t.std()), float(res[y:y + th, x:x + tw].std())))
    stats.sort(key=lambda s: s[0])           # flattest tiles first
    flat = [s[1] for s in stats[:max(1, len(stats) // 5)]]
    return float(np.mean(flat))


def analyze(rec):
    path, name = rec["path"], rec["file"]
    try:
        rgb = load_half(path)
        H, W = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        # ---- sharpness / blur
        s_glob, s_best, tgrad = sharpness_metrics(gray)

        # ---- exposure & tone
        lum = gray.astype(np.float32) / 255.0
        p = np.percentile(gray, [1, 5, 25, 50, 75, 95, 99]).tolist()
        mean_l = float(lum.mean())
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
        total = hist.sum()
        clip_hi = float(hist[254:].sum() / total)
        clip_lo = float(hist[:2].sum() / total)
        contrast_std = float(gray.std())
        dyn_range = float((p[6] - p[0]) / 255.0)
        # entropy = tonal information
        pr = hist / total
        entropy = float(-(pr[pr > 0] * np.log2(pr[pr > 0])).sum())

        # ---- colour
        b, g, r = [float(rgb[:, :, i].mean()) for i in (2, 1, 0)]
        rg = rgb[:, :, 0].astype(np.float32) - rgb[:, :, 1]
        yb = 0.5 * (rgb[:, :, 0].astype(np.float32) + rgb[:, :, 1]) - rgb[:, :, 2]
        colorfulness = float(np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                             + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        saturation = float(hsv[:, :, 1].mean())
        gray_world = [round(r / max(g, 1e-6), 4), 1.0, round(b / max(g, 1e-6), 4)]

        # ---- faces. Two detectors with different failure modes:
        #  blaze  = high precision, near/large faces only  -> crop geometry
        #  haar   = catches distant faces but noisy        -> weak crowd hint only
        bf = blaze_faces(rgb)
        fc, pc = cascades()
        sc = 1000.0 / max(W, H)
        small = cv2.equalizeHist(cv2.resize(gray, (int(W * sc), int(H * sc)),
                                            interpolation=cv2.INTER_AREA))
        haar = fc.detectMultiScale(small, 1.1, 5, minSize=(24, 24))
        prof = pc.detectMultiScale(small, 1.1, 5, minSize=(24, 24))
        haar_boxes = [[int(x / sc), int(y / sc), int(w / sc), int(h / sc)] for x, y, w, h in haar]
        n_prof = len(prof)

        frame_area = W * H
        blaze_boxes = [d["box"] for d in bf]
        face_frac = max((w * h / frame_area for _, _, w, h in blaze_boxes), default=0.0)
        haar_frac = max((w * h / frame_area for _, _, w, h in haar_boxes), default=0.0)
        # sharpness measured on the largest confident face only
        face_sharp = None
        ref = blaze_boxes or haar_boxes
        if ref:
            x, y, w, h = max(ref, key=lambda f: f[2] * f[3])
            crop = gray[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
            if crop.size > 100:
                face_sharp = float(cv2.Laplacian(crop, cv2.CV_32F).var())

        # ---- perceptual hashes
        pil_small = Image.fromarray(rgb).resize((256, 256), Image.LANCZOS)
        hashes = {
            "phash": str(imagehash.phash(pil_small, hash_size=16)),
            "dhash": str(imagehash.dhash(pil_small, hash_size=16)),
            "ahash": str(imagehash.average_hash(pil_small, hash_size=16)),
            "colorhash": str(imagehash.colorhash(pil_small, binbits=3)),
        }

        return {
            "file": name, "ok": True,
            "analysis_dims": [W, H],
            "sharpness_global": round(s_glob, 2),
            "sharpness_best_region": round(s_best, 2),
            "tenengrad": round(tgrad, 2),
            "face_sharpness": round(face_sharp, 2) if face_sharp is not None else None,
            "noise": round(noise_estimate(gray), 3),
            "mean_luma": round(mean_l, 4),
            "percentiles": [round(v, 1) for v in p],
            "clip_high": round(clip_hi, 5),
            "clip_low": round(clip_lo, 5),
            "contrast_std": round(contrast_std, 2),
            "dynamic_range": round(dyn_range, 4),
            "entropy": round(entropy, 3),
            "rgb_means": [round(r, 2), round(g, 2), round(b, 2)],
            "gray_world_ratio": gray_world,
            "colorfulness": round(colorfulness, 2),
            "saturation": round(saturation, 2),
            "n_faces_blaze": len(bf), "blaze_faces": bf,
            "n_faces_haar": len(haar_boxes), "n_profile_faces": n_prof,
            "haar_faces": haar_boxes,
            "largest_face_frac": round(face_frac, 5),
            "largest_haar_face_frac": round(haar_frac, 5),
            **hashes,
        }
    except Exception as e:  # noqa: BLE001
        return {"file": name, "ok": False, "error": repr(e)}


def main():
    inv = json.loads((ANALYSIS / "photo_inventory.json").read_text())
    print(f"analyzing {len(inv)} images on 4 workers ...")
    out = []
    with Pool(4) as pool:
        for i, r in enumerate(pool.imap(analyze, inv, chunksize=8), 1):
            out.append(r)
            if i % 100 == 0:
                print(f"  {i}/{len(inv)}")
    (ANALYSIS / "photo_technical.json").write_text(json.dumps(out, indent=1))

    good = [r for r in out if r["ok"]]
    bad = [r for r in out if not r["ok"]]
    print(f"\nanalyzed ok: {len(good)}   failed: {len(bad)}")
    for r in bad:
        print("   FAIL", r["file"], r.get("error"))
    if not good:
        return
    arr = lambda k: np.array([r[k] for r in good if r.get(k) is not None], dtype=float)  # noqa: E731
    for k in ("sharpness_best_region", "face_sharpness", "mean_luma", "clip_high", "clip_low",
              "contrast_std", "noise", "colorfulness", "entropy", "largest_face_frac"):
        a = arr(k)
        if a.size:
            print(f"{k:22} n={a.size:4d} min={a.min():9.3f} p25={np.percentile(a,25):9.3f} "
                  f"med={np.median(a):9.3f} p75={np.percentile(a,75):9.3f} max={a.max():9.3f}")
    print(f"\nblaze: images with >=1 face {sum(1 for r in good if r['n_faces_blaze'])}, "
          f"total {sum(r['n_faces_blaze'] for r in good)}")
    print(f"haar : images with >=1 face {sum(1 for r in good if r['n_faces_haar'])}, "
          f"total {sum(r['n_faces_haar'] for r in good)}")


if __name__ == "__main__":
    main()
