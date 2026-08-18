"""STAGE 10-13: PAGE COMPOSITION (incl. portrait reframing and spreads).

Renders every planned page from the edited TIFF intermediates at trim+bleed.
Face boxes are re-detected on the graded image so crops centre on the real
faces, and every placement is logged with its scale factor so effective print
resolution can be audited afterwards.

Writes album/pages/page_NNN.jpg, output/album_pages/, analysis/composition_log.json
"""
import json
import os
import sys
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import layout as L
from config import (ALBUM, ANALYSIS, DPI, JPEG_QUALITY_PAGE, OUTPUT, PAGE_H_BLEED,
                    PAGE_W_BLEED, WORK)

Image.MAX_IMAGE_PIXELS = None
PAGES = ALBUM / "pages"
PAGES.mkdir(parents=True, exist_ok=True)
OUT_PAGES = OUTPUT / "album_pages"
OUT_PAGES.mkdir(parents=True, exist_ok=True)
_blaze = {}


def faces_of(rgb):
    """Re-detect faces on the graded image (BlazeFace, high precision)."""
    if "d" not in _blaze:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mpp
            from mediapipe.tasks.python import vision
            _blaze["mp"] = mp
            _blaze["d"] = vision.FaceDetector.create_from_options(
                vision.FaceDetectorOptions(
                    base_options=mpp.BaseOptions(
                        model_asset_path=str(Path(__file__).parent.parent / "models"
                                             / "blaze_face_short_range.tflite")),
                    min_detection_confidence=0.45))
        except Exception:  # noqa: BLE001
            _blaze["d"] = None
    det, mp = _blaze.get("d"), _blaze.get("mp")
    if det is None:
        return []
    H, W = rgb.shape[:2]
    s = min(1.0, 768.0 / max(W, H))
    small = cv2.resize(rgb, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA)
    try:
        res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                  data=np.ascontiguousarray(small)))
    except Exception:  # noqa: BLE001
        return []
    inv = 1.0 / s
    return [[int(d.bounding_box.origin_x * inv), int(d.bounding_box.origin_y * inv),
             int(d.bounding_box.width * inv), int(d.bounding_box.height * inv)]
            for d in res.detections]


def load_edited(f):
    p = WORK / "edited" / f.replace(".JPG", ".tif")
    return np.asarray(Image.open(p).convert("RGB"))


def save_page(img: Image.Image, n: int):
    name = f"page_{n:03d}.jpg"
    img.save(PAGES / name, quality=JPEG_QUALITY_PAGE, subsampling=1, optimize=True)
    img.save(OUT_PAGES / name, quality=JPEG_QUALITY_PAGE, subsampling=1, optimize=True)
    return name


def main():
    plan = json.loads((ANALYSIS / "album_plan.json").read_text())
    selections = json.loads((ANALYSIS / "selections.json").read_text())
    sel = {p["file"]: p for p in selections["selected"]}
    chapter_titles = {c["key"]: c["title"] for c in selections["chapters"]}

    cache, log = {}, []
    for sheet in plan["pages"]:
        L.PLACEMENTS.clear()
        items = []
        for ph in sheet["photos"]:
            f = ph["file"]
            if f not in cache:
                img = load_edited(f)
                cache[f] = {"img": img, "faces": faces_of(img)}
            items.append({"img": cache[f]["img"], "faces": cache[f]["faces"], "file": f})

        lay = sheet["layout"]
        names = []
        if lay == "cover":
            page = L.L_cover(items[0], "A Wedding in Telangana", "the wedding album",
                             "12 June 2020")
            names.append(save_page(page, sheet["pages"][0]))
        elif lay == "closing":
            page = L.L_closing(items[0], "with love")
            names.append(save_page(page, sheet["pages"][0]))
        elif lay == "spread":
            pl, pr = L.L_spread(items[0], chapter=sheet.get("title"))
            names.append(save_page(pl, sheet["pages"][0]))
            names.append(save_page(pr, sheet["pages"][1]))
        else:
            kw = {}
            if sheet.get("title") and lay in ("full_bleed", "duo_editorial", "trio_hband"):
                kw = {"title": sheet["title"], "subtitle": sheet.get("subtitle")}
            if lay in ("portrait_showcase", "portrait_showcase_l"):
                # every showcase page carries a typographic mark, so the ivory
                # column reads as a designed margin rather than an unfilled gap
                kw = {"caption": sheet.get("title") or chapter_titles.get(sheet["chapter"]),
                      "subtitle": sheet.get("subtitle")}
            page = L.render(lay, items, order=sheet.get("cell_order"), **kw)
            names.append(save_page(page, sheet["pages"][0]))

        placements = [dict(p) for p in L.PLACEMENTS]
        for k, p in enumerate(placements):
            # place() tags each placement with its source file; fall back to the
            # planned order only if a tag is missing
            p["file"] = p.get("tag") or sheet["photos"][min(k, len(sheet["photos"]) - 1)]["file"]
            # effective print resolution of the placed crop
            p["effective_dpi"] = int(round(DPI / max(p["scale"], 1e-6))) if p["scale"] > 0 else None
        log.append({
            "pages": sheet["pages"], "layout": lay, "chapter": sheet["chapter"],
            "files": [ph["file"] for ph in sheet["photos"]],
            "page_files": names,
            "purpose": sheet["storytelling_purpose"],
            "placements": placements,
        })
        print(f"  p{sheet['pages'][0]:>3} {lay:18} {len(items)} photo(s) -> {', '.join(names)}")

    (ANALYSIS / "composition_log.json").write_text(json.dumps(log, indent=1))

    up = [(p["file"], p["scale"], p["effective_dpi"])
          for e in log for p in e["placements"] if p["upscaled"]]
    allp = [p for e in log for p in e["placements"]]
    print(f"\nrendered {sum(len(e['page_files']) for e in log)} page images at "
          f"{PAGE_W_BLEED}x{PAGE_H_BLEED} px (trim + bleed)")
    print(f"placements: {len(allp)}")
    sc = np.array([p["scale"] for p in allp])
    print(f"placement scale: min={sc.min():.3f} med={np.median(sc):.3f} max={sc.max():.3f}")
    print(f"upscaled placements: {len(up)}")
    for f, s, d in sorted(up, key=lambda x: -x[1]):
        print(f"   {f}  x{s:.2f}  effective {d} DPI")
    ak = np.array([p["area_kept"] for p in allp])
    print(f"area kept by crops: min={ak.min():.2f} med={np.median(ak):.2f} max={ak.max():.2f}")


if __name__ == "__main__":
    main()
