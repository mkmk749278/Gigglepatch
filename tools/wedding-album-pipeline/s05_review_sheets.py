"""STAGE 5b: build annotated review sheets for the human/vision curation pass.

Every wedding-story cluster representative is laid out chronologically with its
id, capture time, technical score and close-up flag, so selection can be made on
visual evidence with the measurements visible alongside.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from config import ALBUM, ANALYSIS, INPUT_DIR

Image.MAX_IMAGE_PIXELS = None
CELL = 300
COLS = 6
ROWS = 9
LABEL = 24
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 17)
FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 19)


def main():
    sl = json.loads((ANALYSIS / "shortlist.json").read_text())
    inv = {r["file"]: r for r in json.loads((ANALYSIS / "photo_inventory.json").read_text())}
    reps = sl["representatives"]
    reps.sort(key=lambda s: (inv[s["file"]]["capture_ts"] or 0, s["file"]))
    out_dir = ALBUM / "previews" / "review"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    per = COLS * ROWS
    sheets = []
    for si in range(0, len(reps), per):
        chunk = reps[si:si + per]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * CELL, rows * (CELL + LABEL) + 34), (16, 16, 18))
        d = ImageDraw.Draw(sheet)
        day0 = chunk[0]["event_day"]
        d.text((8, 8), f"REVIEW SHEET {si//per+1}   frames {si+1}-{si+len(chunk)} of {len(reps)}"
                       f"   day {day0}", font=FONT_B, fill=(255, 214, 140))
        for k, s in enumerate(chunk):
            f = s["file"]
            im = Image.open(INPUT_DIR / f)
            im.draft("RGB", (CELL * 2, CELL * 2))
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((CELL - 8, CELL - 8), Image.LANCZOS)
            cx = (k % COLS) * CELL
            cy = (k // COLS) * (CELL + LABEL) + 34
            sheet.paste(im, (cx + (CELL - im.width) // 2, cy + (CELL - im.height) // 2))
            t = (s["datetime"] or "")[11:16]
            flags = []
            if s["closeup"]:
                flags.append("CU")
            if s["orientation"] == "portrait":
                flags.append("P")
            if s["group_size"] > 1:
                flags.append(f"x{s['group_size']}")
            lab = f"{f[4:8]} {t} t{s['technical_score']:.2f} f{s['n_faces_blaze']} {' '.join(flags)}"
            col = (255, 234, 190) if s["technical_score"] >= 0.72 else (188, 188, 192)
            d.text((cx + 5, cy + CELL + 2), lab, font=FONT, fill=col)
        p = out_dir / f"review_{si//per+1:02d}.jpg"
        sheet.save(p, quality=80, optimize=True)
        sheets.append(p)
        print(f"{p.name}  {len(chunk)} frames  {p.stat().st_size//1024} KB  {sheet.size}")
    print(f"\n{len(sheets)} sheets covering {len(reps)} representatives")


if __name__ == "__main__":
    main()
