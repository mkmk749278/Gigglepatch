"""STAGE 6: FINAL SELECTION SCORING.

Combines the measured technical score (s04) with the authored visual scores
(curation.py) using the weighting from the brief. Emotion and storytelling carry
more weight than technical quality, so a slightly soft frame with real feeling
can outrank a clean but empty one — which is exactly what happens to several of
the close-ups here.

Writes analysis/selections.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import ANALYSIS
from curation import CHAPTERS, CLOSING, COVER, SELECTION, WEIGHTS


def main():
    scores = {r["file"]: r for r in json.loads((ANALYSIS / "photo_scores.json").read_text())}
    inv = {r["file"]: r for r in json.loads((ANALYSIS / "photo_inventory.json").read_text())}
    tech = {r["file"]: r for r in json.loads((ANALYSIS / "photo_technical.json").read_text())
            if r["ok"]}

    chapter_order = {k: i for i, (k, _, _) in enumerate(CHAPTERS)}
    out, missing = [], []
    for (f, chap, cat, role, emo, comp, story, suit, note) in SELECTION:
        if f not in scores:
            missing.append(f)
            continue
        s, m, t = scores[f], inv[f], tech[f]
        final = (WEIGHTS["technical"] * s["technical_score"]
                 + WEIGHTS["composition"] * comp / 10.0
                 + WEIGHTS["emotion"] * emo / 10.0
                 + WEIGHTS["storytelling"] * story / 10.0
                 + WEIGHTS["uniqueness"] * s["uniqueness_score"]
                 + WEIGHTS["suitability"] * suit / 10.0)
        out.append({
            "file": f,
            "path": m["path"],
            "chapter": chap, "chapter_index": chapter_order[chap],
            "category": cat, "role": role,
            "datetime": m["datetime_original"], "event_day": m["event_day"],
            "orientation": m["orientation"],
            "resolution": f'{m["width"]}x{m["height"]}',
            "width": m["width"], "height": m["height"],
            "technical_score": s["technical_score"],
            "emotion_score": emo, "composition_score": comp,
            "storytelling_score": story, "album_suitability": suit,
            "uniqueness_score": s["uniqueness_score"],
            "final_score": round(final, 4),
            "closeup": s["closeup"], "face_dominant": s["face_dominant"],
            "largest_face_frac": s["largest_face_frac"],
            "n_faces_blaze": t["n_faces_blaze"],
            "faces": [d["box"] for d in t["blaze_faces"]],
            "analysis_dims": t["analysis_dims"],
            "note": note,
        })
    if missing:
        print("WARNING: curated files not found in scores:", missing)

    out.sort(key=lambda r: (r["chapter_index"], r["datetime"] or ""))
    payload = {
        "weights": WEIGHTS,
        "chapters": [{"key": k, "title": t, "dateline": d} for k, t, d in CHAPTERS],
        "cover": COVER, "closing": CLOSING,
        "selected": out,
    }
    (ANALYSIS / "selections.json").write_text(json.dumps(payload, indent=1))

    from collections import Counter
    print(f"selected {len(out)} photographs from 775 originals")
    print("\nby role     :", dict(Counter(r["role"] for r in out)))
    print("by category :", dict(Counter(r["category"] for r in out)))
    print("by orient.  :", dict(Counter(r["orientation"] for r in out)))
    print("\nper chapter:")
    for k, t, d in CHAPTERS:
        n = sum(1 for r in out if r["chapter"] == k)
        print(f"   {k:18} {t:22} {n:3d}")
    print("\ntop 15 by final score:")
    for r in sorted(out, key=lambda r: -r["final_score"])[:15]:
        print(f"   {r['file'][4:8]} {r['final_score']:.3f} tech={r['technical_score']:.2f} "
              f"emo={r['emotion_score']:2d} {r['role']:8} {r['chapter']:16} {r['note'][:52]}")
    print("\nlowest 5 by final score (kept for story, not for polish):")
    for r in sorted(out, key=lambda r: r["final_score"])[:5]:
        print(f"   {r['file'][4:8]} {r['final_score']:.3f} tech={r['technical_score']:.2f} "
              f"emo={r['emotion_score']:2d} {r['role']:8} {r['note'][:52]}")


if __name__ == "__main__":
    main()
