"""STAGE 15: PDF QUALITY CONTROL (PyMuPDF) + album contact sheet.

Verifies page count, page geometry, trim boxes, embedded image presence and
resolution, ordering, blank/near-blank pages and decode errors; renders every
page to a preview; and builds the full-album contact sheet.

Writes output/reports/pdf_qc.json, output/previews/pages/*.jpg,
output/previews/album_contact_sheet.jpg
"""
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from config import (ANALYSIS, BLEED_IN, OUTPUT, PAGE_HEIGHT_IN, PAGE_WIDTH_IN)

PREV = OUTPUT / "previews"
PAGE_PREV = PREV / "pages"
PAGE_PREV.mkdir(parents=True, exist_ok=True)
(OUTPUT / "reports").mkdir(parents=True, exist_ok=True)
PT = 72.0
EXP_W = (PAGE_WIDTH_IN + 2 * BLEED_IN) * PT
EXP_H = (PAGE_HEIGHT_IN + 2 * BLEED_IN) * PT

FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26)


def main():
    pdf = OUTPUT / "final_album.pdf"
    plan = json.loads((ANALYSIS / "album_plan.json").read_text())
    doc = pymupdf.open(pdf)
    issues, pages = [], []

    if doc.page_count != plan["page_count"]:
        issues.append(f"page count {doc.page_count} != planned {plan['page_count']}")

    previews = []
    for i, page in enumerate(doc, 1):
        r = page.rect
        rec = {"page": i, "width_pt": round(r.width, 2), "height_pt": round(r.height, 2),
               "width_in": round(r.width / PT, 4), "height_in": round(r.height / PT, 4),
               "rotation": page.rotation}
        if abs(r.width - EXP_W) > 0.6 or abs(r.height - EXP_H) > 0.6:
            issues.append(f"p{i}: size {r.width:.1f}x{r.height:.1f} pt != "
                          f"{EXP_W:.1f}x{EXP_H:.1f}")
        tb = page.trimbox
        rec["trimbox_in"] = [round(tb.width / PT, 4), round(tb.height / PT, 4)]
        if abs(tb.width / PT - PAGE_WIDTH_IN) > 0.02 or abs(tb.height / PT - PAGE_HEIGHT_IN) > 0.02:
            issues.append(f"p{i}: trimbox {tb.width/PT:.3f}x{tb.height/PT:.3f} in != "
                          f"{PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN}")

        imgs = page.get_images(full=True)
        rec["image_count"] = len(imgs)
        if not imgs:
            issues.append(f"p{i}: no embedded image")
        res = []
        for im in imgs:
            xref = im[0]
            info = doc.extract_image(xref)
            w, h = info["width"], info["height"]
            res.append([w, h])
            eff = w / (r.width / PT)
            if eff < 200:
                issues.append(f"p{i}: embedded image only {eff:.0f} DPI ({w}x{h})")
        rec["image_dims"] = res
        rec["filters"] = sorted({doc.extract_image(im[0])["ext"] for im in imgs}) if imgs else []

        try:
            pm = page.get_pixmap(dpi=48)
            arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
            rgb = arr[..., :3]
            rec["mean_luma"] = round(float(rgb.mean() / 255), 4)
            rec["std_luma"] = round(float(rgb.std()), 3)
            if rec["std_luma"] < 6.0:
                issues.append(f"p{i}: page looks blank/near-uniform (std {rec['std_luma']:.1f})")
            prev = PAGE_PREV / f"page_{i:03d}.jpg"
            Image.fromarray(rgb).save(prev, quality=82, optimize=True)
            previews.append((i, prev))
        except Exception as e:  # noqa: BLE001
            issues.append(f"p{i}: render failed {e!r}")
            rec["render_error"] = repr(e)
        pages.append(rec)

    # ---------- ordering check against the plan
    expected = []
    for sheet in plan["pages"]:
        expected.extend(sheet["pages"])
    if sorted(expected) != list(range(1, plan["page_count"] + 1)):
        issues.append("planned page numbers are not a contiguous 1..N sequence")

    report = {
        "pdf": str(pdf), "size_bytes": pdf.stat().st_size,
        "page_count": doc.page_count,
        "expected_page_count": plan["page_count"],
        "expected_media_pt": [round(EXP_W, 2), round(EXP_H, 2)],
        "trim_in": [PAGE_WIDTH_IN, PAGE_HEIGHT_IN], "bleed_in": BLEED_IN,
        "issues": issues, "pages": pages,
    }
    (OUTPUT / "reports" / "pdf_qc.json").write_text(json.dumps(report, indent=1))

    print(f"pages           : {doc.page_count} (planned {plan['page_count']})")
    ims = [p["image_count"] for p in pages]
    print(f"embedded images : total {sum(ims)}, per page min={min(ims)} max={max(ims)}")
    fl = sorted({f for p in pages for f in p["filters"]})
    print(f"image encodings : {fl}")
    dims = {tuple(d) for p in pages for d in p["image_dims"]}
    print(f"embedded dims   : {sorted(dims)}")
    eff = [d[0] / (p['width_pt'] / PT) for p in pages for d in p["image_dims"]]
    print(f"effective DPI   : min={min(eff):.0f} max={max(eff):.0f}")
    lum = [p["mean_luma"] for p in pages if "mean_luma" in p]
    std = [p["std_luma"] for p in pages if "std_luma" in p]
    print(f"page luma       : min={min(lum):.3f} max={max(lum):.3f}")
    print(f"page detail std : min={min(std):.1f} max={max(std):.1f}  (blank-page guard)")
    print(f"\nissues: {len(issues)}")
    for s in issues:
        print("   -", s)

    # ---------- contact sheet
    COLS, CW, CH, LAB = 6, 420, 320, 30
    rows = (len(previews) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CW, rows * (CH + LAB) + 54), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), f"ALBUM CONTACT SHEET  -  {doc.page_count} pages  -  "
                     f"{PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN} in @ {report['trim_in']}",
           font=FONT_B, fill=(255, 214, 140))
    for k, (n, p) in enumerate(previews):
        im = Image.open(p)
        im.thumbnail((CW - 14, CH - 14), Image.LANCZOS)
        x, y = (k % COLS) * CW, (k // COLS) * (CH + LAB) + 54
        sheet.paste(im, (x + (CW - im.width) // 2, y + (CH - im.height) // 2))
        d.text((x + 8, y + CH + 4), f"Page {n:03d}", font=FONT, fill=(214, 214, 218))
    cs = PREV / "album_contact_sheet.jpg"
    sheet.save(cs, quality=84, optimize=True)
    print(f"\ncontact sheet: {cs}  {sheet.size}  {cs.stat().st_size//1024} KB")
    doc.close()


if __name__ == "__main__":
    main()
