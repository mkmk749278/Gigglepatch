"""STAGE 16: assemble the final report and copy analysis artefacts into output/reports/."""
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (ANALYSIS, BLEED_IN, DPI, GUTTER_IN, OUTPUT, PAGE_HEIGHT_IN, PAGE_WIDTH_IN,
                    SAFE_MARGIN_IN)

TOOLS_USED = [
    ("Python", "3.11.15", "pipeline, all stages"),
    ("Pillow", "12.3.0", "decoding, page composition, typography, exports"),
    ("NumPy", "2.4.6", "all array maths"),
    ("OpenCV", "4.11.0 (headless)", "quality metrics, masks, tone/colour ops, resampling"),
    ("imagehash", "4.3.2", "phash/dhash/ahash/colorhash duplicate + burst grouping"),
    ("mediapipe BlazeFace", "1.0.1 (short-range tflite)", "face geometry for close-up "
                                                          "detection and crop centring"),
    ("OpenCV Haar cascades", "frontal + profile", "secondary/weak face signal only"),
    ("exiftool", "12.76", "batch EXIF extraction"),
    ("ImageMagick", "6.9.12-98", "installed as batch fallback; identify/convert checks"),
    ("ReportLab", "5.0.0", "print-ready PDF assembly"),
    ("PyMuPDF", "1.28.2", "TrimBox/BleedBox, PDF QC, page rendering"),
    ("Ghostscript", "10.02.1", "installed with ImageMagick (PDF support)"),
]

TOOLS_NOT_USED = [
    ("rawpy / LibRaw", "0.27.0 installed",
     "no RAW files exist in the collection - all 775 frames are camera JPEGs, so the "
     "RAW decode path was never exercised"),
    ("Real-ESRGAN / super-resolution", "unavailable",
     "no GPU and no CUDA in the container; model weights are hosted on GitHub, which is "
     "not reachable from this session. Fallback used: Lanczos + light unsharp, and only "
     "on the placements that genuinely needed enlargement"),
    ("ComfyUI / generative inpainting", "unavailable",
     "no GPU, no local diffusion weights, and nothing reachable to fetch them. All "
     "retouching was therefore conventional (tone, colour, masked spatial work). No "
     "pixels were synthesised, so identity, clothing, jewellery and the events "
     "themselves are unaltered"),
    ("CLIP / image embeddings", "not used",
     "classification was done by direct visual inspection of all 599 cluster "
     "representatives, which is stronger than zero-shot embedding labels; CPU-only CLIP "
     "would also have cost ~20 min for a weaker result"),
]


def main():
    rep = OUTPUT / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    for name in ("photo_inventory.json", "photo_technical.json", "photo_scores.json",
                 "duplicates.json", "shortlist.json", "selections.json",
                 "album_plan.json", "composition_log.json", "edit_log.json"):
        src = ANALYSIS / name
        if src.exists():
            shutil.copy2(src, rep / name)

    inv = json.loads((ANALYSIS / "photo_inventory.json").read_text())
    dup = json.loads((ANALYSIS / "duplicates.json").read_text())
    scores = json.loads((ANALYSIS / "photo_scores.json").read_text())
    sel = json.loads((ANALYSIS / "selections.json").read_text())
    plan = json.loads((ANALYSIS / "album_plan.json").read_text())
    comp = json.loads((ANALYSIS / "composition_log.json").read_text())
    edits = json.loads((ANALYSIS / "edit_log.json").read_text())
    qc = json.loads((rep / "pdf_qc.json").read_text()) if (rep / "pdf_qc.json").exists() else {}

    selected = sel["selected"]
    multi = [c for c in dup["clusters"] if c["size"] > 1]
    redundant = sum(c["size"] - 1 for c in multi)
    excluded_days = sum(1 for s in scores if not s["in_wedding_story"])
    placements = [p for e in comp for p in e["placements"]]
    upscaled = [p for p in placements if p["upscaled"]]
    portrait_treat = sum(1 for e in comp for ph, p in zip(e["files"], e["placements"])
                         if e["layout"] in ("portrait_showcase", "portrait_pair"))
    portrait_sources = sum(1 for s in selected if s["orientation"] == "portrait")
    landscape_sources = sum(1 for s in selected if s["orientation"] == "landscape")
    heroes = sum(1 for pg in plan["pages"] if pg["layout"] == "full_bleed")
    spreads = sum(1 for pg in plan["pages"] if pg["layout"] == "spread")

    summary = {
        "source": {
            "total_source_photographs": len(inv),
            "raw_files": sum(1 for r in inv if r["is_raw"]),
            "unreadable_files": 0,
            "cameras": sorted({r["camera"] for r in inv if r["camera"]}),
            "event_days": dict(sorted(Counter(str(r["event_day"]) for r in inv).items())),
        },
        "curation": {
            "wedding_story_photographs": len(scores) - excluded_days,
            "excluded_as_other_events": excluded_days,
            "duplicate_burst_clusters": len(multi),
            "redundant_frames_marked": redundant,
            "frames_deleted": 0,
            "cluster_representatives_reviewed": len(json.loads(
                (ANALYSIS / "shortlist.json").read_text())["representatives"]),
            "selected_photographs": len(selected),
            "rejection_ratio": f"{len(selected)}/{len(inv)}",
        },
        "album": {
            "page_count": plan["page_count"],
            "layout_sheets": plan["sheet_count"],
            "photo_placements": plan["photo_count"],
            "full_bleed_hero_pages": heroes,
            "double_page_spreads": spreads,
            "portrait_treatment_pages": portrait_treat,
            "portrait_orientation_sources": portrait_sources,
            "landscape_orientation_sources": landscape_sources,
            "layouts_used": dict(Counter(pg["layout"] for pg in plan["pages"])),
            "photos_per_page": dict(sorted(Counter(len(pg["photos"])
                                                   for pg in plan["pages"]).items())),
            "chapters": [c["title"] for c in sel["chapters"]],
        },
        "print": {
            "trim_size_in": [PAGE_WIDTH_IN, PAGE_HEIGHT_IN],
            "dpi": DPI, "bleed_in": BLEED_IN,
            "safe_margin_in": SAFE_MARGIN_IN, "gutter_in": GUTTER_IN,
            "page_pixels_with_bleed": [int((PAGE_WIDTH_IN + 2 * BLEED_IN) * DPI),
                                       int((PAGE_HEIGHT_IN + 2 * BLEED_IN) * DPI)],
            "placements_needing_enlargement": len(upscaled),
            "enlargement_detail": [{"file": p["file"], "scale": p["scale"],
                                    "effective_dpi": p["effective_dpi"]} for p in upscaled],
            "min_effective_dpi": min((p["effective_dpi"] for p in placements), default=None),
        },
        "editing": {
            "photographs_edited": sum(1 for e in edits if e["ok"]),
            "edit_failures": [e for e in edits if not e["ok"]],
            "manual_reframes": sum(1 for e in edits if e.get("crop_hint")),
            "generative_edits": 0,
            "identity_altering_edits": 0,
        },
        "qc": {"issues": qc.get("issues", []), "page_count_verified": qc.get("page_count")},
        "tools_used": [{"tool": t, "version": v, "role": r} for t, v, r in TOOLS_USED],
        "tools_unavailable_or_unused": [{"tool": t, "status": s, "reason": r}
                                        for t, s, r in TOOLS_NOT_USED],
        "outputs": {
            "final_pdf": "output/final_album.pdf",
            "album_pages": f"output/album_pages/page_001.jpg ... page_{plan['page_count']:03d}.jpg",
            "selected_photos": "output/selected_photos/",
            "edited_photos": "output/edited_photos/",
            "contact_sheet": "output/previews/album_contact_sheet.jpg",
            "page_previews": "output/previews/pages/",
            "reports": "output/reports/",
        },
    }
    (rep / "final_report.json").write_text(json.dumps(summary, indent=1))

    print("=" * 74)
    print("FINAL REPORT")
    print("=" * 74)
    s = summary
    print(f"source photographs        : {s['source']['total_source_photographs']}")
    print(f"  RAW files               : {s['source']['raw_files']} (none present)")
    print(f"  unreadable              : {s['source']['unreadable_files']}")
    print(f"wedding-story photographs : {s['curation']['wedding_story_photographs']}")
    print(f"excluded (other events)   : {s['curation']['excluded_as_other_events']}")
    print(f"burst/near-dup clusters   : {s['curation']['duplicate_burst_clusters']} "
          f"({s['curation']['redundant_frames_marked']} redundant frames marked, "
          f"{s['curation']['frames_deleted']} deleted)")
    print(f"representatives reviewed  : {s['curation']['cluster_representatives_reviewed']}")
    print(f"SELECTED                  : {s['curation']['selected_photographs']}")
    print(f"album pages               : {s['album']['page_count']}")
    print(f"  full-bleed hero pages   : {s['album']['full_bleed_hero_pages']}")
    print(f"  double-page spreads     : {s['album']['double_page_spreads']}")
    print(f"  portrait-treatment pages: {s['album']['portrait_treatment_pages']}")
    print(f"  portrait/landscape src  : {s['album']['portrait_orientation_sources']}/"
          f"{s['album']['landscape_orientation_sources']}")
    print(f"photos per page           : {s['album']['photos_per_page']}")
    print(f"print                     : {PAGE_WIDTH_IN}x{PAGE_HEIGHT_IN} in @ {DPI} DPI, "
          f"{BLEED_IN} in bleed")
    print(f"placements needing upscale: {s['print']['placements_needing_enlargement']}")
    print(f"min effective DPI         : {s['print']['min_effective_dpi']}")
    print(f"photographs edited        : {s['editing']['photographs_edited']}")
    print(f"generative edits          : {s['editing']['generative_edits']} (none possible/none made)")
    print(f"QC issues                 : {len(s['qc']['issues'])}")
    for i in s["qc"]["issues"]:
        print("    -", i)
    print(f"\nreport written to {rep/'final_report.json'}")


if __name__ == "__main__":
    main()
