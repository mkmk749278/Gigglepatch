"""Album print configuration. All print geometry is configurable here — nothing hard-coded downstream."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input" / "original_photos"
ANALYSIS = ROOT / "analysis"
SELECTED = ROOT / "selected"
EDITED = ROOT / "edited"
ALBUM = ROOT / "album"
OUTPUT = ROOT / "output"
WORK = ROOT / "work"

# ---------------------------------------------------------------- PRINT CONFIG
# Physical album size. Landscape 12 x 9 inch is a standard luxury wedding format
# and is chosen here because the 4288x2848 (3:2) Nikon D90 source frames fill a
# 4:3 page at 300 DPI with NO upscaling required.
PAGE_WIDTH_IN = 12.0
PAGE_HEIGHT_IN = 9.0
DPI = 300
BLEED_IN = 0.125       # 3.175 mm trim bleed
SAFE_MARGIN_IN = 0.375  # keep critical content inside this
GUTTER_IN = 0.5        # binding allowance at spine (per spread)

# Derived pixel geometry
PAGE_W = int(round(PAGE_WIDTH_IN * DPI))          # 3600
PAGE_H = int(round(PAGE_HEIGHT_IN * DPI))         # 2700
BLEED_PX = int(round(BLEED_IN * DPI))             # 38
SAFE_PX = int(round(SAFE_MARGIN_IN * DPI))        # 112
GUTTER_PX = int(round(GUTTER_IN * DPI))           # 150
PAGE_W_BLEED = PAGE_W + 2 * BLEED_PX
PAGE_H_BLEED = PAGE_H + 2 * BLEED_PX

# Album visual identity
PAPER = (252, 250, 247)      # warm ivory stock
INK = (38, 34, 30)           # warm near-black text
INK_SOFT = (135, 124, 112)   # caption grey
RULE = (206, 194, 180)       # hairline rule

JPEG_QUALITY_PAGE = 95       # album page JPEGs
JPEG_QUALITY_EXPORT = 92     # selected/edited exports

# Analysis decode scale: all sources are exactly 4288x2848, so a 1/2-scale
# decode gives a uniform 2144x1424 basis => metrics are directly comparable.
ANALYSIS_LONG_EDGE = 2144

RAW_EXTS = {".nef", ".cr2", ".cr3", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"} | RAW_EXTS

for d in (ANALYSIS, SELECTED, EDITED, ALBUM, OUTPUT, WORK):
    d.mkdir(parents=True, exist_ok=True)
