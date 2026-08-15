# GigglePatch — Handoff

### Written 2026-08-15 · read this first, then `ACTIVE_CONTEXT.md`

This is the state of the channel and everything built for it. `CLAUDE.md` is the
standing project reference; `ACTIVE_CONTEXT.md` is the live status board.
This file explains *why* things are the way they are, so nobody has to
rediscover it.

---

## WHERE THE PROJECT IS

**Primary line:** *Tara and the Star Lantern* — interactive preschool, Made for
Kids: Yes. Two episodes fully written. Tara's character art is generated and
rigged. Nothing is published yet.

**Scout line:** paused, fully preserved, not cancelled. Episode 1 "The Lost Map"
is written and unstarted in `episodes/ep01-the-lost-map/`. Do not delete it.

**Published so far:** two kids songs. Neither uses any of the machinery below.

---

## THE CENTRAL DECISION: TWO ROUTES, BOTH LIVE

The series can be made two ways, and both are built. They are not rivals — the
sensible end state uses each where it is strong.

| | **Puppet route** | **Flow route** |
|---|---|---|
| How | Cut-out animation, rendered offline | Google Flow generates video clips |
| Character consistency | Perfect, permanently | Good, never guaranteed |
| Cost per episode | Zero | Flow credits |
| Motion quality | Only as good as the rig | Genuinely cinematic |
| Backgrounds | Currently weak | Excellent |
| Best at | Character performance, dialogue, the interactive beats | Establishing shots, atmosphere, crowds, anything with complex motion |

The puppet route exists because of a hard constraint the user set: *"we need to
achieve without flow."* It works today, offline, with no credits.

### Why not frame-by-frame image generation

Asked and answered — see `tools/ANIMATION_APPROACH.md`. Image models have no
temporal model, an episode is roughly 7,000 frames, and the character drifts
between every one of them. It never converges. This is not a prompt problem.

### Why cut-out puppetry specifically

Because it is what shows of this format have always actually used — parts with
pivots, arranged in a hierarchy, rotated over time. The artwork never changes,
so the character *physically cannot* drift, flicker or age between frames. The
failure modes that make per-frame generation unusable do not exist.

---

## WHAT IS BUILT

### The animation engine

| File | What it does |
|---|---|
| `tools/puppet.py` | The engine. `Part`, `Rig`, world-transform resolution, `Camera`, `render_video` |
| `tools/tara_rig.py` | Tara + Chikoo drawn in code as placeholders. Holds the animations: `call_out_pause()`, `walk_cycle()` |
| `tools/tara_photo_rig.py` | **Tara built from the real generated artwork.** This is the one that matters now |
| `tools/scenes.py` | Four locations, three times of day, ground shadows, scrolling backgrounds |
| `tools/episode.py` | Shot list → one MP4. Multi-shot assembly with no video model |

### The art pipeline

| File | What it does |
|---|---|
| `tools/autorig.py` | Cuts one A-pose image into rig parts by analysing the silhouette. Also the magenta chroma key |
| `tools/cut_strip.py` | Cuts a row of small objects (mouths, lantern stages) into separate PNGs |
| `tools/continuity_check.py` | Frame-to-frame QC for generated clips: JUMP / FLICKER / DRIFT / FREEZE |

### The prompts

| File | What it is |
|---|---|
| `series-tara/MODEL_SHEET_PROMPTS.md` | **Start here.** One prompt per character, each producing a complete model sheet in a single generation |
| `series-tara/NANO_BANANA_PROMPTS.md` | The same thing done step by step, for finer per-panel control |
| `series-tara/PART_SET_PROMPTS.md` | Individual part prompts. Largely superseded by the two above |
| `series-tara/CHARACTER_REFERENCE_PROMPTS.md` | Flow Characters-tab descriptions, with accept/reject checklists |

### The assets

```
series-tara/reference/nano_banana_v1/   20 generated images, Tara
series-tara/reference/parts/            6 mouth shapes, 4 lantern stages
series-tara/reference/parts/body/       6 rig parts + rig.json
```

---

## HOW TO PICK IT UP

```bash
# see the rig assembled from the real art — every rotation at zero
python3 tools/tara_photo_rig.py assembly assembly_check.png

# render the CALL-OUT PAUSE, 10s at 1080p, ~60 seconds
python3 tools/tara_photo_rig.py callout tara_callout.mp4

# cut a new character's A-pose
python3 tools/autorig.py <apose.jpeg> series-tara/reference/parts/<name>/
python3 -c "import sys; sys.path.insert(0,'tools'); from autorig import annotate; \
            annotate('<apose.jpeg>','check.jpg')"
```

**Always run the assembly check before animating.** Joints are named once in
source-image coordinates, so a zero-rotation pose reassembles the source image
exactly. That makes the check meaningful: any visible seam is a real error, not
a judgement call.

---

## WHAT IS NEXT, IN ORDER

1. **Background art.** The character is now a premium render and the locations
   behind her are shapes drawn in code. That mismatch is the most visible
   problem in any frame. Backgrounds need no rigging, no cutting and no
   cross-pose consistency, so this is the cheapest quality win available
2. **Elbow and knee joints.** The arm currently swings from the shoulder as one
   piece, so the lantern points sideways instead of lifting to chest height.
   `walk_cycle()` and `call_out_pause()` already have `fore_l` / `fore_r` tracks
   written — split the parts and the bend appears with no animation edits
3. **The rest of the cast** — Ravi, Chikoo, Kaaki, Nandu, Ammamma. Same
   one-prompt sheet each. Check Ravi against Tara at thumbnail size
4. **Two rejected expressions** — curious came back in an orange top, surprised
   in a different render style. Curious matters most; it is the CALL-OUT PAUSE
5. **The voice** — see below. This is the real blocker on a finished episode

---

## THE OPEN DECISION: THE VOICE

This is the one thing that cannot be worked around, and it is not a technical
problem.

The format is *interactive* — Tara asks the viewer a question and waits. That
requires speech. Three options, all with costs:

| Option | Cost |
|---|---|
| Record a human voice | Needs a person and a microphone, every episode, forever |
| TTS | Cheap and repeatable, but preschool audiences respond to warmth and most TTS has none |
| Near-wordless | Works, costs nothing, and throws away most of the format's value |

The VO script is written for both episodes and can be laid over finished clips
without regenerating anything — so this blocks *publishing*, not production.
Everything else can proceed while it is undecided.

---

## HARD-WON LESSONS — DO NOT REDISCOVER THESE

### Prompting

- **Flow and Nano Banana lock onto the first strong association they recognise.**
  Every character description leads with unique visual anchors — braids and
  ribbons, the star lantern, the grey neck collar, the crescent horns — and never
  with role, species or nationality. Leading with "Indian girl" renders an adult
  woman in bridal wear. Leading with "girl explorer" collides with existing IP
- **End-of-prompt negatives are weighted heavily.** The trailing NOT clauses are
  load-bearing, not decoration. Never trim them
- **"Old woman" pulls toward frail, stooped and sad.** Ammamma needs three
  explicit negatives to stay upright and capable
- **"Crow" pulls toward gothic and horror.** Kaaki needs four non-menacing cues
  before the style block. A frightening antagonist ends a preschool channel

### Generating art for a rig

- **The A-pose gaps are a technical requirement, not a style choice.** The cutter
  finds limbs as separate runs of opaque pixels across each scanline. Arms flat
  against the sides leave no seam to cut along
- **Empty hands, braids behind the shoulders.** Anything in the arm zone gets cut
  out *with* the arm and welded to it permanently
- **Ask for the A-pose as its own full-frame image.** Inside a model sheet it is
  a few hundred pixels tall — not enough to cut from
- **Never bake shadows into part artwork.** The rig rotates limbs; a shadow cast
  to one side will point the wrong way in every frame of every episode. Light the
  composited frame instead

### Code

- **Chroma-key the background, do not measure distance from a corner colour.**
  Generated backgrounds come back as gradients — 205 to 241 across one frame —
  which is outside any tolerance tight enough to keep black hair. `min(R,B) - G`
  puts magenta near 150 and every colour on the cast at or below zero, and being
  a channel ratio it barely moves under a gradient
- **Scale is inherited down the hierarchy.** Set it on the root only, or it is
  squared once per level of nesting
- **Arm crops overlap the torso deliberately** so the shoulder does not gap when
  it rotates — but that overlap must be erased below the shoulder, or it is a
  full-height strip of tunic that swings with the arm
- **Blur the distance field in `_volumize`** or the medial axis prints a visible
  crease down every boxy shape
- **`continuity_check` FLICKER cannot be sign flips in a difference curve.**
  Independent per-frame noise produces a *constant* high difference, not an
  oscillating one. It measures pixels that change where optical flow says
  nothing moved
- **`continuity_check` JUMP compares to a local neighbourhood, not a global
  median** — otherwise a real gesture in an otherwise still shot reads as a
  discontinuity
- **OpenCV 5.0 dropped `CascadeClassifier`.** Pin `opencv-python-headless<5`

---

## COMPLIANCE — NON-NEGOTIABLE

`FLOW_COMPLIANCE.md` governs every prompt. The parts that have already come up:

- **No named characters from other IP.** Two requests were declined on this
  basis: animating a Dora poster (Paramount IP → Content ID → strikes → channel
  risk), and it stays declined
- **No realistic depictions of children.** Every Tara prompt carries an explicit
  *NOT photorealistic / NOT a real child / NOT live action* clause. This is not
  caution, it is §2's absolute prohibition, and stylised animation is the
  compliant route to the same creative goal. Photorealistic AI children were
  requested once and declined
- **Reference images from other shows:** render quality, lighting and polish are
  free to aim at. Faces, silhouettes, clothing, logos and signature props are
  not. Never upload another show's character into a Flow reference slot
- **YouTube AI disclosure is required on every upload** — the Studio toggle and
  the description line, both

### Repository workflow

Feature branch always, PR for every change, update `ACTIVE_CONTEXT.md` on every
PR, compliance check before writing any prompt.

---

## WHAT IS NOT IN THIS REPO

A separate wedding-photo project ran in the same sessions and lives entirely
outside it, in `/home/user/wedding/` — culling, per-photo grading and album
layout for the user's marriage and baby-ceremony photos. It shares no code and
no purpose with GigglePatch. Deliverables were uploaded to a file host and
expire without downloads; they are not part of the channel and are not tracked
here.
