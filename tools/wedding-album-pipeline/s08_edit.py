"""STAGE 9: EDIT ONLY THE SELECTED PHOTOGRAPHS.

Runs the cinematic grade at full resolution on the 89 selected frames (not on
all 775 - selection precedes editing so no compute is spent on frames that will
never reach a page). Originals are never modified; results are written as
lossless TIFF intermediates for composition plus delivery JPEGs.

Writes work/edited/*.tif, output/edited_photos/*.jpg,
output/selected_photos/*.jpg, analysis/edit_log.json
"""
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import cv2
import numpy as np
from PIL import Image, ImageOps

cv2.setNumThreads(1)
sys.path.insert(0, str(Path(__file__).parent))
import grade as G
from config import ANALYSIS, JPEG_QUALITY_EXPORT, OUTPUT, WORK

Image.MAX_IMAGE_PIXELS = None
EDIT_DIR = WORK / "edited"
EDIT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT / "edited_photos").mkdir(parents=True, exist_ok=True)
(OUTPUT / "selected_photos").mkdir(parents=True, exist_ok=True)


def load_full(path):
    im = Image.open(path)
    return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))


def apply_crop_hint(rgb, hint, faces):
    """hint = (x0,y0,x1,y1) as fractions of the frame. Crops only."""
    if not hint:
        return rgb, faces
    H, W = rgb.shape[:2]
    x0, y0, x1, y1 = hint
    X0, Y0 = int(round(x0 * W)), int(round(y0 * H))
    X1, Y1 = int(round(x1 * W)), int(round(y1 * H))
    X0, Y0 = max(0, X0), max(0, Y0)
    X1, Y1 = min(W, X1), min(H, Y1)
    if X1 - X0 < 32 or Y1 - Y0 < 32:
        return rgb, faces
    out = rgb[Y0:Y1, X0:X1]
    moved = []
    for (fx, fy, fw, fh) in faces:
        nx, ny = fx - X0, fy - Y0
        # keep only faces still fully inside the crop
        if nx >= 0 and ny >= 0 and nx + fw <= (X1 - X0) and ny + fh <= (Y1 - Y0):
            moved.append([nx, ny, fw, fh])
    return out, moved


def profile_for(role):
    if role in ("hero", "spread", "cover", "closing"):
        return "hero"
    if role == "detail":
        return "detail"
    return "default"


def work(rec):
    f = rec["file"]
    try:
        rgb = load_full(rec["path"])
        H, W = rgb.shape[:2]

        # face boxes were measured on the half-scale analysis image
        aw, ah = rec["analysis_dims"]
        sx, sy = W / aw, H / ah
        faces = [[int(b[0] * sx), int(b[1] * sy), int(b[2] * sx), int(b[3] * sy)]
                 for b in rec.get("faces", [])]

        rgb, faces = apply_crop_hint(rgb, rec.get("crop_hint"), faces)

        # untouched-but-selected export for traceability
        Image.fromarray(rgb).save(OUTPUT / "selected_photos" / f.replace(".JPG", ".jpg"),
                                  quality=JPEG_QUALITY_EXPORT, subsampling=1, optimize=True)

        tech = rec["_tech"]
        out, prm, gains = G.grade(rgb, tech, faces=faces, profile=profile_for(rec["role"]))

        # lossless intermediate used by the layout engine
        tif = EDIT_DIR / f.replace(".JPG", ".tif")
        Image.fromarray(out).save(tif, compression="tiff_lzw")
        Image.fromarray(out).save(OUTPUT / "edited_photos" / f.replace(".JPG", ".jpg"),
                                  quality=JPEG_QUALITY_EXPORT, subsampling=1, optimize=True)

        g0 = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        g1 = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY)
        return {
            "file": f, "ok": True, "role": rec["role"],
            "profile": profile_for(rec["role"]),
            "crop_hint": rec.get("crop_hint"),
            "edited_dims": [out.shape[1], out.shape[0]],
            "faces_used": len(faces),
            "wb_gains": [round(float(x), 4) for x in gains],
            "params": prm,
            "mean_luma_before": round(float(g0.mean() / 255), 4),
            "mean_luma_after": round(float(g1.mean() / 255), 4),
            "clip_high_before": round(float((g0 >= 254).mean()), 5),
            "clip_high_after": round(float((g1 >= 254).mean()), 5),
            "clip_low_after": round(float((g1 <= 1).mean()), 5),
            "tif": str(tif),
        }
    except Exception as e:  # noqa: BLE001
        return {"file": f, "ok": False, "error": repr(e)}


def main():
    sel = json.loads((ANALYSIS / "selections.json").read_text())
    plan = json.loads((ANALYSIS / "album_plan.json").read_text())
    tech = {r["file"]: r for r in json.loads((ANALYSIS / "photo_technical.json").read_text())
            if r["ok"]}
    hints = {}
    for pg in plan["pages"]:
        for ph in pg["photos"]:
            hints[ph["file"]] = ph.get("crop_hint")

    recs = []
    for p in sel["selected"]:
        recs.append({**p, "crop_hint": hints.get(p["file"]), "_tech": tech[p["file"]]})

    print(f"editing {len(recs)} selected photographs (full resolution) on 3 workers ...")
    results = []
    with Pool(3) as pool:
        for i, r in enumerate(pool.imap_unordered(work, recs, chunksize=1), 1):
            results.append(r)
            if i % 10 == 0:
                print(f"  {i}/{len(recs)}")

    results.sort(key=lambda r: r["file"])
    (ANALYSIS / "edit_log.json").write_text(json.dumps(results, indent=1))
    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    print(f"\nedited ok: {len(ok)}   failed: {len(bad)}")
    for r in bad:
        print("   FAIL", r["file"], r.get("error"))
    if ok:
        st = np.array([r["params"]["stops"] for r in ok])
        sh = np.array([r["params"]["shadows"] for r in ok])
        hl = np.array([r["params"]["highlight_strength"] for r in ok])
        dn = sum(1 for r in ok if r["params"]["noise"] > G.NOISE_REF * 1.15)
        cb = np.array([r["clip_high_before"] for r in ok])
        ca = np.array([r["clip_high_after"] for r in ok])
        print(f"exposure stops   min={st.min():+.2f} med={np.median(st):+.2f} max={st.max():+.2f}")
        print(f"shadow lift      min={sh.min():.2f} med={np.median(sh):.2f} max={sh.max():.2f}")
        print(f"highlight rolloff med={np.median(hl):.2f} max={hl.max():.2f}")
        print(f"denoised frames  {dn}/{len(ok)} (only above the measured noise median)")
        print(f"clipped highlights: before med={np.median(cb)*100:.2f}%  "
              f"after med={np.median(ca)*100:.2f}%")
        wb = np.array([r["wb_gains"] for r in ok])
        print(f"wb gain range    R {wb[:,0].min():.3f}-{wb[:,0].max():.3f}  "
              f"B {wb[:,2].min():.3f}-{wb[:,2].max():.3f}")
        print(f"frames with a manual crop hint: {sum(1 for r in ok if r['crop_hint'])}")


if __name__ == "__main__":
    main()
