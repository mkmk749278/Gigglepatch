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

---

# The other route: cut-out puppet animation

## How Dora was actually made

**Not frame by frame.** Dora the Explorer was produced as **cut-out puppet
animation in Adobe Flash**: each character is built *once* as a rig of separate
pieces — head, torso, upper arm, forearm, thigh, shin, plus a library of
swappable mouth shapes — connected in a hierarchy. Animation is then rotating
and moving those pieces over time. The 2024 reboot moved to 3D CGI, same
principle with a 3D rig instead of flat pieces.

That is why hundreds of episodes were economically possible. Nobody redrew Dora
for every frame; they posed a puppet.

## Why this matters more than it sounds

The artwork never changes between frames. So the character **physically cannot**
drift, boil, age, or change costume — the failure modes that make per-frame
image generation unusable do not exist in this technique. Not "are reduced".
Do not exist.

| | Per-frame generation | Flow | Cut-out puppet |
|---|---|---|---|
| Character consistency | Poor — drifts | Good within a shot | **Perfect, by construction** |
| Cost per episode | Enormous | Moderate credits | **Zero** |
| Control over exact pose | None | Indirect | **Total, to the frame** |
| Policy risk | High | Low | **None** |
| Runs offline | No | No | **Yes** |
| Art effort up front | None | Low | **High — needs a part set** |
| Camera moves, depth, lighting | Free | Free | Must be built |

The cost is real and it is at the front: somebody has to produce clean character
art cut into separate parts on transparent backgrounds. After that, every
episode is free forever.

## We have a working engine

`tools/puppet.py` — the rig engine. Parts with pivots, parent/child hierarchy,
keyframe tracks, easing, and direct render to MP4 through ffmpeg.

`tools/tara_rig.py` — Tara as a 12-part puppet, and the CALL-OUT PAUSE animated
over ten seconds at 24fps.

```bash
python3 tools/tara_rig.py out.mp4
```

Renders 240 frames at 1920×1080 in about seventy seconds on this machine, with
no network and no credits.

### What the proof clip contains

Idle breathing → lantern lifted beside her face → head tilts into the question →
**three full seconds of hold** → wave → settle. That is the exact beat that
appears three times in every episode of the series.

### What it proves

- The hierarchy works: rotate the torso and the head, braids, arms and lantern
  all follow
- Follow-through works: the braids lag behind the head, which is what sells
  weight
- The lantern stays upright in world space while the arm rotates underneath it,
  because it hangs from a ring handle
- `continuity_check.py` reports it clean apart from the deliberate three-second
  hold, which it correctly identifies as a FREEZE

### The art is placeholder, and deliberately so

Every part is drawn in code as flat shapes, so the pipeline runs today with
nothing to download. To move to real art, replace each `_draw_*` function with a
PNG loaded from `series-tara/reference/parts/`, keep the pivot and attach
points, and **every animation in the file keeps working unchanged**. That
separation is the entire point of a rig: art and performance are independent.

### What a real part set needs

Generated in ImageFX, each on a transparent background, in a consistent style:

```
head_front.png      torso.png         upper_arm.png     forearm_hand.png
head_3quarter.png   braid.png         thigh.png         shin_shoe.png
mouth_*.png (a set of shapes for speech)   lantern_unlit.png / lantern_lit.png
```

Flat, even lighting, no baked shadows — the rig supplies the motion, so the art
must not carry any.

## Which route to take

They are not exclusive, and the honest answer is that they suit different shots:

- **Flow** for establishing shots, scenery, atmosphere, anything with real
  depth, camera movement or complex lighting — the things a flat puppet cannot
  do
- **Puppet** for character performance: dialogue, the CALL-OUT PAUSE, reactions,
  anything repeated every episode where consistency matters more than spectacle

A series that used the puppet for its recurring character beats and Flow for its
wide shots would be cheaper, more consistent and faster to produce than either
approach alone.
