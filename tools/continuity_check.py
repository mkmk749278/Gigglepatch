"""Frame-to-frame continuity checker for generated clips.

This is steps 7 and 8 of the frame-by-frame workflow — "inspect 001 -> 002 ->
003, look for sudden jumps, character changes, distorted limbs" — done
automatically, and applied to the clips a video model produces rather than to
7,000 individually generated stills.

What it flags:

  JUMP     a hard discontinuity: the picture changed far more between two
           frames than the clip's own normal rate of change
  FLICKER  boiling / shimmer: the frame difference oscillates up and down
           every frame or two while nothing is actually moving. This is the
           signature failure of image-model-per-frame animation
  DRIFT    the colour identity of the frame has wandered away from where the
           clip started — characters slowly changing costume or skin tone
  FREEZE   a run of near-identical frames, i.e. the motion stalled

Run it on RAW single shots straight out of Flow, before grading and before
assembly:

    python3 tools/continuity_check.py shot_07.mp4
    python3 tools/continuity_check.py shots/*.mp4 --json report.json

Two things will produce false alarms if you point it at the wrong material:

  * A finished multi-shot edit trips DRIFT and FREEZE by design, because the
    picture is *supposed* to change completely at every cut and hold still on
    title cards. Check shots individually instead.
  * Added film grain is per-frame random noise, which is boiling by definition.
    Check before grading, or raise --flicker.
"""
import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np


def frame_stats(path, max_side=480):
    """Per-frame difference, flow magnitude and colour signature."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f'cannot open {path}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    diffs, flows, hists, statics = [], [], [], []
    prev_small = prev_gray = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        s = max_side / max(h, w)
        small = cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
        hists.append(cv2.normalize(hist, hist).flatten())

        if prev_small is not None:
            pix = np.abs(small.astype(np.float32) - prev_small.astype(np.float32)).mean(axis=2)
            diffs.append(float(pix.mean()))
            f = cv2.calcOpticalFlowFarneback(prev_gray, gray, None,
                                             0.5, 3, 15, 3, 5, 1.2, 0)
            mag = np.linalg.norm(f, axis=2)
            flows.append(float(mag.mean()))
            # How much do pixels change where nothing actually moved? That is
            # the definition of boiling: resynthesis without motion. Normalise
            # by the frame's own contrast so it is comparable across clips.
            still_px = mag < 0.5
            contrast = float(gray.std()) or 1.0
            statics.append(float(pix[still_px].mean() / contrast)
                           if still_px.sum() > 64 else 0.0)
        prev_small, prev_gray = small, gray
    cap.release()
    return (fps, np.array(diffs), np.array(flows), np.array(hists),
            np.array(statics))


def analyse(path, jump_z=4.0, flicker=0.055, drift_thresh=0.45):
    """flicker is the allowed change in non-moving pixels, as a fraction of
    frame contrast. Above it, the picture is boiling rather than moving."""
    fps, diffs, flows, hists, statics = frame_stats(path)
    n = len(diffs) + 1
    findings = []
    if len(diffs) < 4:
        return dict(path=path, frames=n, fps=fps, findings=[], verdict='TOO SHORT')

    med = float(np.median(diffs))
    mad = float(np.median(np.abs(diffs - med))) or 1e-6
    # A clip that is frozen for much of its length has a median of ~0, which
    # would make every relative threshold collapse. Use an upper percentile as
    # the reference for "how much this clip normally changes".
    ref = float(np.percentile(diffs, 75)) or med or 1e-6

    # --- JUMP: an isolated spike, judged against its own neighbourhood ---
    # A gesture is *sustained* elevated change over many frames; a real
    # discontinuity is one frame that does not belong. Comparing against the
    # clip's global median flags every genuine movement in an otherwise still
    # shot, so compare each frame to its local neighbours instead, excluding
    # itself.
    half = 6
    for i, d in enumerate(diffs):
        lo, hi = max(0, i - half), min(len(diffs), i + half + 1)
        neigh = np.concatenate([diffs[lo:i], diffs[i + 1:hi]])
        if len(neigh) < 4:
            continue
        nmed = float(np.median(neigh))
        nmad = float(np.median(np.abs(neigh - nmed))) or 1e-6
        z = (d - nmed) / (1.4826 * nmad)
        if z > jump_z and d > nmed * 2.0 and d > med * 1.5:
            findings.append(dict(kind='JUMP', frame=i + 2,
                                 time=round((i + 1) / fps, 2), score=round(float(z), 1)))

    # --- FLICKER: pixels change where nothing moved ---
    # Real motion changes pixels along moving edges only; the rest of the frame
    # stays put. Per-frame resynthesis re-rolls texture everywhere, so even
    # perfectly still regions keep changing. That is what this measures.
    if len(statics) >= 6:
        boil = float(np.median(statics))
        if boil > flicker:
            findings.append(dict(kind='FLICKER', frame=None, time=None,
                                 score=round(boil, 3),
                                 note='still areas keep changing — picture is boiling'))

    # --- DRIFT: colour signature wanders away from the opening frames ---
    base = hists[:max(3, len(hists) // 20)].mean(axis=0)
    sims = np.array([cv2.compareHist(base.astype(np.float32), h.astype(np.float32),
                                     cv2.HISTCMP_CORREL) for h in hists])
    if sims.min() < drift_thresh:
        i = int(sims.argmin())
        findings.append(dict(kind='DRIFT', frame=i + 1, time=round(i / fps, 2),
                             score=round(float(sims.min()), 2),
                             note='colour identity moved away from the clip opening'))

    # --- FREEZE: a run of frames with essentially no change ---
    # Relative only — an absolute floor mislabels quiet clips as frozen. Judge
    # on a rolling median so a single compression spike inside a held frame
    # does not split one freeze into several short ones.
    k = 5
    pad = np.pad(diffs, (k // 2, k // 2), mode='edge')
    smooth = np.array([np.median(pad[i:i + k]) for i in range(len(diffs))])
    still = smooth < ref * 0.25
    run = best = 0
    best_at = 0
    for i, s in enumerate(still):
        run = run + 1 if s else 0
        if run > best:
            best, best_at = run, i
    if best >= max(int(fps * 0.5), 6):
        findings.append(dict(kind='FREEZE', frame=best_at - best + 2,
                             time=round((best_at - best + 1) / fps, 2),
                             score=best, note=f'{best} near-identical frames'))

    verdict = 'CLEAN' if not findings else (
        'REGENERATE' if any(f['kind'] in ('JUMP', 'FLICKER') for f in findings) else 'REVIEW')
    return dict(path=path, frames=n, fps=round(fps, 2), median_diff=round(med, 2),
                findings=findings, verdict=verdict)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clips', nargs='+', help='video files (globs allowed)')
    ap.add_argument('--json', help='write the full report here')
    ap.add_argument('--flicker', type=float, default=0.055,
                    help='boiling threshold (default 0.055). Raise for footage '
                         'that already has film grain added')
    ap.add_argument('--jump', type=float, default=4.0,
                    help='jump sensitivity in robust z-units (default 4.0)')
    args = ap.parse_args()

    paths = []
    for c in args.clips:
        paths.extend(sorted(glob.glob(c)) or [c])

    reports = []
    for p in paths:
        if not os.path.exists(p):
            print(f'  missing: {p}')
            continue
        try:
            r = analyse(p, jump_z=args.jump, flicker=args.flicker)
        except Exception as e:
            print(f'  {os.path.basename(p)}: ERROR {e}')
            continue
        reports.append(r)

        mark = {'CLEAN': 'ok  ', 'REVIEW': 'hmm ', 'REGENERATE': 'BAD '}[r['verdict']]
        print(f"{mark} {os.path.basename(p):<34} {r['frames']:>5} frames @ {r['fps']}fps"
              f"   {r['verdict']}")
        for f in r['findings']:
            where = f'frame {f["frame"]} ({f["time"]}s)' if f['frame'] else 'whole clip'
            note = f'  — {f["note"]}' if f.get('note') else ''
            print(f"       {f['kind']:<8} {where:<22} score {f['score']}{note}")

    if args.json:
        json.dump(reports, open(args.json, 'w'), indent=1)
        print(f'\nwrote {args.json}')

    bad = sum(1 for r in reports if r['verdict'] == 'REGENERATE')
    if reports:
        print(f"\n{len(reports)} clips · {sum(1 for r in reports if r['verdict']=='CLEAN')} clean"
              f" · {bad} need regenerating")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
