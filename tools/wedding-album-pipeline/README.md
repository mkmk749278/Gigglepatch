# Cinematic Wedding Album Pipeline

A self-contained, CPU-only pipeline that turns a folder of unsorted wedding
photographs into a print-ready album PDF. Built and run against a 775-frame
Nikon D90 collection; nothing in it is specific to that shoot except
`curation.py`, which holds the per-photograph editorial judgements.

## Design principles

- **Originals are immutable.** `input/original_photos/` is set read-only and is
  never written to. Every derived file is traceable:
  `original -> selected -> edited -> album placement`.
- **Select before you edit.** Technical analysis and curation run over the whole
  collection, but the expensive full-resolution grade only touches the frames
  that actually reach a page.
- **Measure, then calibrate.** Thresholds (noise, close-up size, perceptual-hash
  distance) are derived from this collection's own measured distributions rather
  than hard-coded guesses. See the comments in `grade.py` and `s03_duplicates.py`.
- **No synthesised pixels.** All retouching is conventional tone/colour/spatial
  work. No generative editing, no invented detail, no identity changes.
- **Print geometry is configuration, not code.** `config.py` owns page size, DPI,
  bleed, safe margin and gutter.

## Stages

| Script | Stage |
|---|---|
| `s01_discover.py` | recursive discovery, dimensions, orientation, RAW detection, EXIF via exiftool |
| `s02_analyze.py`  | OpenCV quality metrics (multi-metric), perceptual hashes, face geometry |
| `s03_duplicates.py` | exact / near-duplicate / burst grouping (nothing deleted) |
| `s04_score.py`    | percentile-rank technical scoring, narrative moment segmentation, shortlist |
| `s05_review_sheets.py` | annotated contact sheets for the visual curation pass |
| `curation.py`     | authored per-photograph scores, chapters, roles, reframing hints |
| `s06_select.py`   | weighted final scoring (emotion and storytelling outweigh technical) |
| `s07_plan.py`     | story order and page planning; layout chosen from content |
| `s08_edit.py`     | full-resolution cinematic grade of selected frames only |
| `s09_compose.py`  | page composition, portrait reframing, double-page spreads |
| `s10_pdf.py`      | ReportLab PDF with MediaBox = trim + bleed and a real TrimBox |
| `s11_qc.py`       | PyMuPDF verification + page previews + album contact sheet |
| `s12_report.py`   | final report assembly |

Run them in order; each persists its output as JSON under `analysis/` so the
pipeline can be resumed or re-run stage by stage.

## The colour pipeline (`grade.py`)

Tone work happens in **linear light**, contrast and grading in perceptual sRGB.
Per-image parameters are derived from that image's own statistics, so the grade
adapts to each lighting environment instead of stamping one LUT everywhere.

Two failure modes that had to be engineered around, both documented inline:

1. **Grey-world white balance is wrong for this material.** The frames are
   dominated by warm content (gold, red silk, skin, terracotta), so a global
   average reads the *subject* as a colour cast and over-corrects toward cyan —
   gilding turns teal and a pink saree rotates to violet. The estimator instead
   samples only genuinely near-neutral pixels, skips correction entirely when the
   frame has no neutral reference, and clamps gains to ±7%.
2. **Forcing a target median luminance destroys the key.** High-key studio frames
   are legitimately bright. Exposure is only corrected when the median falls
   outside a comfortable band, and then only as far as the band edge.

Saturation is skin-protected and red-guarded (the saree reds sit at the top of
the gamut and posterise if pushed). Denoising is referenced to the collection's
measured noise median, so the typical frame is left alone — important here,
because everything was shot at ISO 200–250 and the residual is mostly JPEG
texture rather than sensor noise.

## Reframing (`crop.py`)

Crops are chosen by maximising a gradient-energy saliency score with face
containment and rule-of-thirds eye-line placement. A portrait recompose is
rejected unless it keeps at least 34% of the frame area *and* every detected
face survives — otherwise the frame stays landscape. Aspect is always corrected
by cropping, never by non-uniform scaling.

## Requirements

```
pip install pillow numpy opencv-python-headless==4.11.0.86 imagehash \
            reportlab pymupdf scipy rawpy piexif mediapipe
apt-get install imagemagick libimage-exiftool-perl libegl1 libgles2
```

mediapipe needs `blaze_face_short_range.tflite` in `models/`.

GPU is optional and was not available where this was developed; the pipeline is
CPU-only throughout and pins BLAS/tflite thread pools to 1 so its own process
pool does not oversubscribe the machine.
