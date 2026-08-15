# How We Actually Animate — and why not frame-by-frame

## The question

> Generate 240 individual frames for a 10-second clip at 24fps, each one a
> continuation of the previous, then combine them into an MP4.

## The answer: no, and here is why

### 1. Image models have no temporal model

Feeding frame 86 back in to produce frame 87 does not create continuity. It
creates **drift plus flicker**. Every generation re-synthesises skin texture,
hair strands, fabric weave and eye highlights slightly differently, because the
model is sampling afresh each time. At 24fps that reads as violent boiling
shimmer — the single most recognisable failure mode of AI animation.

The golden rule stated as *"FRAME N must look like the natural continuation of
FRAME N-1"* is exactly right as a goal. The problem is that an image model has
no mechanism to honour it. Nothing in its architecture knows what motion is.

### 2. The arithmetic does not close

| | |
|---|---|
| Episode 1 runtime | ~290 seconds |
| At 24fps | **~7,000 frames** |
| Each generated, inspected, and bad ones regenerated | — |
| And each regeneration introduces *fresh* inconsistency | so it never converges |

Even at a wildly optimistic ten seconds per frame including review, that is
about twenty hours of continuous work for one episode, before any of it is any
good.

### 3. Video models already solve this

Flow generates temporally coherent motion directly — it models movement, not
just appearance. That is the entire reason it exists, and why an 8–10 second
Flow clip looks smooth while 240 stitched stills do not.

---

## What IS right about the frame-by-frame workflow

Steps 1 to 4 are real animation practice and we use all of them:

| Step | Verdict | How we do it |
|---|---|---|
| 1. Final character design, kept consistent | ✅ Correct | `series-tara/CHARACTER_BIBLE.md` + locked reference images |
| 2. Decide the complete action first | ✅ Correct | The shot block, written before any generation |
| 3. Create the key poses | ✅ Correct | One Flow shot per beat — 32 of them per episode |
| 4. Generate the in-betweens | ✅ Correct **goal** | Flow does this internally, with a motion model |
| 5. Animate every character and the background | ✅ Correct | Written into each shot prompt as explicit motion |
| 6. Generate 240 frames per 10 seconds | ❌ Wrong method | Flow outputs the frames; we never author them |
| 7. Check frame-to-frame continuity | ✅ Correct | **Automated — `continuity_check.py`** |
| 8. Fix bad frames | ⚠️ Per shot, not per frame | Regenerate the 8-second clip, not frame 87 |
| 9. Combine in order | ✅ Correct | ffmpeg concat |
| 10. Inspect the final MP4 | ✅ Correct | Always |

**The one real substitution is step 6.** Everything else survives.

---

## Getting the control you actually wanted

The instinct behind the request — *"I want to control the poses, not just
describe a scene and hope"* — is a good one. Flow supports it directly:

- **Start frame.** Give Flow an image and it animates *from* that exact pose.
  This is step 3 → 4 done properly: you author the key pose, the model produces
  the in-betweens.
- **One beat per shot.** Do not ask a single clip for "walks, looks around,
  waves, turns, walks away". Ask for one action. Five separate 8-second clips
  give far more control than one 10-second clip attempting five actions.
- **Name the motion explicitly** in the prompt. Our shot blocks already do this
  — "braids swinging", "tail curls into a question mark", "head-feathers stand
  up and quiver". Motion that is not named does not happen.

---

## Step 7, automated

`tools/continuity_check.py` does the frame-to-frame inspection the workflow asks
for, on the clips Flow produces.

```bash
python3 tools/continuity_check.py shot_07.mp4
python3 tools/continuity_check.py shots/*.mp4 --json report.json
```

It flags four things:

| Flag | Meaning | Verdict |
|---|---|---|
| **JUMP** | A hard discontinuity — the picture changed far more between two frames than this clip's own normal rate | REGENERATE |
| **FLICKER** | Pixels keep changing where optical flow says nothing moved. Boiling | REGENERATE |
| **DRIFT** | Colour identity wandered away from the clip's opening — a character changing costume or skin tone mid-shot | REVIEW |
| **FREEZE** | A run of near-identical frames — motion stalled | REVIEW |

Exit code is non-zero if anything needs regenerating, so it drops into a script
over a whole shot folder.

### Use it on the right material

- **Raw single shots**, straight out of Flow, before grading and before assembly
- **Not** a finished multi-shot edit — that trips DRIFT and FREEZE by design,
  because the picture is supposed to change completely at each cut and hold
  still on title cards
- **Before adding film grain.** Grain is per-frame random noise, which is
  boiling by definition. Raise `--flicker` if you must check graded footage

### Validated against known defects

The detector was built against synthetic clips with deliberately injected
faults, and calibrated until each was caught with no false alarm on the clean
control:

| Test clip | Result |
|---|---|
| Smooth pan, real motion | CLEAN |
| Character teleports at frame 41 | JUMP at frame 41 |
| Per-frame resynthesis noise, static scene | FLICKER, score 0.388 against a 0.055 threshold |
| Motion stalls for 1.5s | FREEZE, 35 frames, plus a JUMP where motion resumes |

Two calibration lessons worth keeping:

- **Counting sign flips in the difference curve does not detect boiling.**
  Independent per-frame noise produces a *constant* high difference, not an
  oscillating one. What actually identifies it is pixels changing in regions
  where optical flow says nothing moved.
- **Freeze detection needs a rolling median.** Compression artifacts put
  isolated spikes inside a held frame, which split one long freeze into several
  short ones that then fall under the reporting threshold.
