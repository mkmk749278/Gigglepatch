"""STAGE 17: PRINT-READY PDF (ReportLab).

MediaBox = trim + bleed, and a TrimBox is written so a printer knows where the
final cut falls. Page JPEGs are embedded directly (DCTDecode) rather than
re-encoded, so the export stage adds no second generation of JPEG loss.

Writes output/final_album.pdf
"""
import json
import sys
from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

sys.path.insert(0, str(Path(__file__).parent))
from config import (ALBUM, ANALYSIS, BLEED_IN, DPI, OUTPUT, PAGE_HEIGHT_IN, PAGE_WIDTH_IN)

PT = 72.0
MEDIA_W = (PAGE_WIDTH_IN + 2 * BLEED_IN) * PT
MEDIA_H = (PAGE_HEIGHT_IN + 2 * BLEED_IN) * PT
TRIM_OFF = BLEED_IN * PT


def main():
    log = json.loads((ANALYSIS / "composition_log.json").read_text())
    pages = []
    for entry in log:
        for n, name in zip(entry["pages"], entry["page_files"]):
            pages.append((n, ALBUM / "pages" / name))
    pages.sort(key=lambda t: t[0])

    missing = [str(p) for _, p in pages if not p.exists()]
    if missing:
        raise SystemExit(f"missing page images: {missing}")

    out = OUTPUT / "final_album.pdf"
    c = rl_canvas.Canvas(str(out), pagesize=(MEDIA_W, MEDIA_H))
    c.setTitle("A Wedding in Telangana - Wedding Album")
    c.setSubject(f"{len(pages)} pages, {PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN} in trim, "
                 f"{BLEED_IN} in bleed, {DPI} DPI")
    c.setAuthor("")
    for n, path in pages:
        # drawImage embeds the JPEG stream directly; no borders, exact fill
        c.drawImage(ImageReader(str(path)), 0, 0, width=MEDIA_W, height=MEDIA_H)
        c.showPage()
    c.save()
    print(f"wrote {out}  ({out.stat().st_size/1e6:.1f} MB, {len(pages)} pages)")
    print(f"MediaBox {MEDIA_W:.1f}x{MEDIA_H:.1f} pt "
          f"({PAGE_WIDTH_IN+2*BLEED_IN}x{PAGE_HEIGHT_IN+2*BLEED_IN} in)")

    # ---- add TrimBox / BleedBox so the file is genuinely print-ready
    try:
        import pymupdf
        doc = pymupdf.open(out)
        trim = f"[{TRIM_OFF:.4f} {TRIM_OFF:.4f} {MEDIA_W-TRIM_OFF:.4f} {MEDIA_H-TRIM_OFF:.4f}]"
        media = f"[0 0 {MEDIA_W:.4f} {MEDIA_H:.4f}]"
        for page in doc:
            doc.xref_set_key(page.xref, "TrimBox", trim)
            doc.xref_set_key(page.xref, "BleedBox", media)
        tmp = out.with_suffix(".tmp.pdf")
        doc.save(tmp, garbage=3, deflate=False)
        doc.close()
        tmp.replace(out)
        print(f"TrimBox set to {trim} on all pages "
              f"({PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN} in trim inside the bleed)")
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: could not set TrimBox ({e!r}); MediaBox still includes bleed")
    print(f"final size: {out.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
