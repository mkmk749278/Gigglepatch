"""STAGE 5a: TECHNICAL SCORING + MOMENT SEGMENTATION + SHORTLIST.

Technical scores use percentile ranks within this collection rather than
absolute thresholds, so "sharp" means sharp *for this camera and these
conditions*. Frames are then grouped into narrative "moments" by capture-time
gaps, and the best frame of each duplicate cluster is promoted, guaranteeing the
shortlist covers the whole story instead of only the sharpest stretches.

Writes analysis/photo_scores.json and analysis/shortlist.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import ANALYSIS

MOMENT_GAP_S = 210.0     # a pause this long starts a new narrative moment

# Days that are not part of the wedding story (see report): a stray set of
# kitten frames on the same card, and a separate baby rice-feeding ceremony.
EXCLUDE_DAYS = {"2020-06-20", "2020-06-21"}


def pct_rank(vals):
    """Map values to 0..1 by rank (ties averaged). Robust to outliers."""
    v = np.asarray(vals, dtype=float)
    order = v.argsort()
    ranks = np.empty(len(v), dtype=float)
    ranks[order] = np.arange(len(v), dtype=float)
    # average ties
    uniq, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    sums = np.zeros(len(uniq))
    np.add.at(sums, inv, ranks)
    means = sums / counts
    return means[inv] / max(len(v) - 1, 1)


def main():
    inv = {r["file"]: r for r in json.loads((ANALYSIS / "photo_inventory.json").read_text())}
    tech = {r["file"]: r for r in json.loads((ANALYSIS / "photo_technical.json").read_text())
            if r["ok"]}
    dup = json.loads((ANALYSIS / "duplicates.json").read_text())
    cluster_of = {}
    for c in dup["clusters"]:
        for f in c["members"]:
            cluster_of[f] = c
    files = [f for f in inv if f in tech]
    files.sort(key=lambda f: (inv[f]["capture_ts"] or 0, f))

    # ---------- sharpness: prefer the face region when a face was found
    sharp_raw = []
    for f in files:
        t = tech[f]
        sharp_raw.append(t["face_sharpness"] if t.get("face_sharpness") else
                         t["sharpness_best_region"])
    r_sharp = pct_rank(sharp_raw)
    r_ten = pct_rank([tech[f]["tenengrad"] for f in files])
    r_ent = pct_rank([tech[f]["entropy"] for f in files])
    noise = np.array([tech[f]["noise"] for f in files])
    r_noise = 1.0 - pct_rank(noise)

    scores = []
    for i, f in enumerate(files):
        t, m = tech[f], inv[f]
        ml = t["mean_luma"]
        # exposure: 1.0 inside a comfortable band, tapering outside
        if 0.32 <= ml <= 0.60:
            expo = 1.0
        elif ml < 0.32:
            expo = max(0.0, 1.0 - (0.32 - ml) / 0.22)
        else:
            expo = max(0.0, 1.0 - (ml - 0.60) / 0.28)
        clip_pen = min(1.0, t["clip_high"] / 0.06) * 0.6 + min(1.0, t["clip_low"] / 0.10) * 0.25
        expo = max(0.0, expo - clip_pen * 0.5)

        contrast = float(np.clip((t["contrast_std"] / 255.0 - 0.12) / 0.18, 0, 1))
        focus = 0.68 * r_sharp[i] + 0.32 * r_ten[i]

        technical = float(np.clip(
            0.42 * focus + 0.24 * expo + 0.14 * contrast + 0.12 * r_noise[i] + 0.08 * r_ent[i],
            0, 1))

        cl = cluster_of.get(f, {"group_id": None, "size": 1, "kind": "single"})
        uniqueness = float(1.0 / np.sqrt(cl["size"]))

        scores.append({
            "file": f,
            "event_day": m["event_day"],
            "datetime": m["datetime_original"],
            "orientation": m["orientation"],
            "resolution": f'{m["width"]}x{m["height"]}',
            "group_id": cl["group_id"], "group_size": cl["size"], "group_kind": cl["kind"],
            "sharpness_rank": round(float(r_sharp[i]), 4),
            "focus_score": round(focus, 4),
            "exposure_score": round(expo, 4),
            "contrast_score": round(contrast, 4),
            "noise_rank": round(float(r_noise[i]), 4),
            "entropy_rank": round(float(r_ent[i]), 4),
            "technical_score": round(technical, 4),
            "uniqueness_score": round(uniqueness, 4),
            "n_faces_blaze": t["n_faces_blaze"],
            "n_faces_haar": t["n_faces_haar"],
            "largest_face_frac": t["largest_face_frac"],
            # A genuine close-up, not merely "a face is visible". Measured
            # distribution: med 0.024 / p75 0.035 / max 0.174, so 0.055 selects
            # roughly the top decile - frames where the face really dominates.
            "closeup": bool(t["largest_face_frac"] >= 0.055),
            "face_dominant": bool(t["largest_face_frac"] >= 0.030),
            "in_wedding_story": m["event_day"] not in EXCLUDE_DAYS,
        })

    # ---------- moment segmentation (within each day)
    by_day = {}
    for s in scores:
        by_day.setdefault(s["event_day"], []).append(s)
    mid = 0
    for day, group in sorted(by_day.items()):
        group.sort(key=lambda s: inv[s["file"]]["capture_ts"] or 0)
        prev = None
        for s in group:
            ts = inv[s["file"]]["capture_ts"] or 0
            if prev is None or ts - prev > MOMENT_GAP_S:
                mid += 1
            s["moment_id"] = f"m{mid:03d}"
            prev = ts
    (ANALYSIS / "photo_scores.json").write_text(json.dumps(scores, indent=1))

    # ---------- shortlist: best frame per cluster, all moments represented
    story = [s for s in scores if s["in_wedding_story"]]
    by_cluster = {}
    for s in story:
        by_cluster.setdefault(s["group_id"] or s["file"], []).append(s)
    reps = []
    for k, members in by_cluster.items():
        members.sort(key=lambda s: -s["technical_score"])
        best = members[0]
        best = {**best, "cluster_members": [m["file"] for m in members]}
        reps.append(best)
    reps.sort(key=lambda s: inv[s["file"]]["capture_ts"] or 0)

    moments = {}
    for s in reps:
        moments.setdefault(s["moment_id"], []).append(s)

    (ANALYSIS / "shortlist.json").write_text(json.dumps(
        {"moment_gap_s": MOMENT_GAP_S, "excluded_days": sorted(EXCLUDE_DAYS),
         "representatives": reps}, indent=1))

    print(f"scored {len(scores)} photos")
    print(f"wedding-story photos      : {len(story)}")
    print(f"excluded days {sorted(EXCLUDE_DAYS)}: {len(scores)-len(story)}")
    print(f"clusters in story         : {len(by_cluster)}")
    print(f"narrative moments         : {len(moments)}")
    ts_ = np.array([s["technical_score"] for s in scores])
    print(f"technical score  min={ts_.min():.3f} p25={np.percentile(ts_,25):.3f} "
          f"med={np.median(ts_):.3f} p75={np.percentile(ts_,75):.3f} max={ts_.max():.3f}")
    print(f"close-ups (face >=2% frame): {sum(s['closeup'] for s in scores)}")
    print("\nmoments per day (representatives):")
    dd = {}
    for s in reps:
        dd.setdefault(s["event_day"], set()).add(s["moment_id"])
    for d in sorted(dd):
        n = sum(1 for s in reps if s["event_day"] == d)
        print(f"   {d}   moments={len(dd[d]):3d}   representatives={n:3d}")


if __name__ == "__main__":
    main()
