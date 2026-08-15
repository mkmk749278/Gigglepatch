# GigglePatch — Active Context
### Last updated: 2026-08-15

> Update this file whenever something changes. It is the single source of truth for what is happening right now.
>
> New here? Read `HANDOFF.md` first — it explains why things are the way they are.

---

## Current Status

**Phase:** *Tara and the Star Lantern* — the channel's primary series
**Immediate priority:** Generate the 10-second test shot — `series-tara/TEST_SHOT.md`
One clip decides whether the 32-shot block is worth generating

### Content lines

| Line | Audience | Made for Kids | Status |
|------|----------|---------------|--------|
| **Tara (preschool)** | **Ages 2–5** | **Yes** | **ACTIVE — Ep. 1 and 2 written** |
| Kids songs | Broad | Yes | 2 uploaded |
| Scout adventures | General audience | No | ⏸️ Paused |

Scout is paused, not cancelled. "The Lost Map" is fully written and unstarted in
`episodes/ep01-the-lost-map/` and can resume at any time. Nothing is deleted.

---

## Videos

| # | Title | Type | Made for Kids | Status |
|---|-------|------|---------------|--------|
| 1 | Down on the Farm 🐓 | Farm animal song | Yes | ✅ Uploaded |
| 2 | Five Little Dinosaurs 🦕 | Dino dance song | Yes | ✅ Uploaded |
| 3 | The Lost Map — Scout vs. GRIMBLE | Adventure episode | No | 🎬 In production |

---

## Flow Session Checklist — Tara (run at the start of every Flow session)

- [ ] Open Characters tab
- [ ] Create/select all six: Tara · Ravi · Chikoo · Kaaki · Nandu · Ammamma
- [ ] Paste each description from `series-tara/CHARACTER_BIBLE.md` **exactly**,
      including the trailing NOT clauses
- [ ] Save all six
- [ ] Generate Tara alone first until she is right — everything is judged against her
- [ ] Then Ravi beside her — check they read as two distinct children at thumbnail size
- [ ] Then the animals, then Ammamma. No crowd shots until all six are locked
- [ ] Then paste the shot block

---

## Tara Series — Design Tracker

**Format:** Interactive preschool — direct address, pause-for-answer, three-stop journey
**Cast:** Tara (lead) · Ravi (friend) · Chikoo (palm squirrel) · Kaaki (crow, the taker) · Nandu (water buffalo) · Ammamma (grandmother)
**World:** Small town at the edge of fields — Blue Door House, Banyan Court, Neem Lane, Stepwell, Mango Grove, Water Tank, Rooftops, Market Lane
**Device:** Five-point brass star lantern — three points light per episode, one per stop

| Item | Status |
|------|--------|
| Character bible | ✅ `series-tara/CHARACTER_BIBLE.md` |
| Reference image prompts | ✅ `series-tara/CHARACTER_REFERENCE_PROMPTS.md` |
| Reference images generated | ⬜ Start with Tara, 8+ attempts |
| **10-second test shot** | ⬜ Flow route — `series-tara/TEST_SHOT.md` |
| Cut-out puppet engine | ✅ `tools/puppet.py` + `tools/tara_rig.py` |
| Puppet: CALL-OUT PAUSE (10s) | ✅ Renders offline, ~70s at 1080p |
| Puppet: walk cycle + scrolling bg (10s) | ✅ Renders clean |
| Puppet part-set prompts | ✅ `series-tara/PART_SET_PROMPTS.md` |
| One-prompt model sheets, all six cast | ✅ `series-tara/MODEL_SHEET_PROMPTS.md` |
| **Tara art generated — 19 images** | ✅ `series-tara/reference/nano_banana_v1/` |
| Mouth shapes cut to parts | ✅ 6 PNGs in `reference/parts/` |
| Lantern stages cut to parts | ✅ 4 PNGs in `reference/parts/` |
| Magenta chroma key + despill | ✅ `autorig.load_rgba`, tested on the real art |
| **Full-resolution A-pose** | ✅ `reference/nano_banana_v1/tara_apose.jpeg` |
| Tara body parts cut from A-pose | ✅ 6 parts in `reference/parts/body/` |
| Photo rig — real art in the puppet | ✅ `tools/tara_photo_rig.py`, assembly clean |
| CALL-OUT PAUSE with real art | ✅ Renders 240 frames in ~60s at 1080p |
| Wave hello (5s) with real art | ✅ `tara_photo_rig.py wave` — courtyard, morning |
| Elbow + knee joints | ⬜ Arm swings as one piece; no elbow bend yet |
| Background art quality | ⬜ **Now the weakest link — coded scenes vs. generated character** |
| Auto-rig from one A-pose image | ✅ `tools/autorig.py`, tested |
| Location art (4 stages) | ✅ `tools/scenes.py` — courtyard, neem lane, mango grove, banyan court |
| Camera (pan / push-in) | ✅ `puppet.Camera` — crops a window from a 2560x1440 stage |
| Chikoo rig | ✅ 3 parts, tail curls into the question mark |
| Multi-shot episode assembly | ✅ `tools/episode.py` — shot list to one MP4, no video model |
| IP safety documented in FLOW_COMPLIANCE §6 | ✅ Done |
| Series format doc | ✅ `series-tara/SERIES_FORMAT.md` |
| Episode 1 shot block | ✅ `series-tara/ep01-three-things/tara_ep01.md` (32 shots) |
| Episode 2 shot block | ✅ `series-tara/ep02-kite-on-the-wire/tara_ep02.md` (32 shots) |
| Music prompt (preschool tone) | ✅ In the Ep. 1 file — BPM 96, acoustic |
| Ep. 1 Flow generation | ⬜ Not started — generate Tara alone first |
| VO recording / TTS decision | ⬜ **Blocked on a decision — see below** |

**Ep. 1 — "Three Things for Ammamma":** Ammamma needs three things. Mangoes from
the grove (count them), Nandu blocks Neem Lane (make a plan), Kaaki takes the
jaggery (clap three times). Ends by leaving a sweet on the wall for Kaaki.

**Decisions still needed:**
- **The voice.** This format needs speech — an interactive show cannot work
  silently the way Scout does. Record it, use TTS, or go near-wordless and lose
  most of the format's value. VO script is written and can be added to finished
  clips without regenerating anything, so this does not block Flow generation
- Confirm character names and series title
- Second-language layer deferred — series works in English, Indian identity
  carried by setting and characters rather than vocabulary

---

## Open Tasks

- [ ] Tara: **generate the 10-second test shot and check it** — walk, stop, turn to camera, lift lantern
- [ ] Tara: generate reference images in ImageFX/Whisk — Tara first, lock her before anything else
- [ ] Tara: run `tools/continuity_check.py` over every Flow shot before assembly
- [ ] Tara: save keepers into `series-tara/reference/` with the fixed filenames
- [ ] Tara: upload references to the Flow Characters tab
- [ ] Tara: generate Ep. 1 Flow clips
- [ ] Tara: decide voice route, then record/synthesise the VO track
- [ ] Tara: generate Ep. 1 music (BPM 96 acoustic prompt)
- [ ] Tara: assemble, compress, upload Ep. 1 — Made for Kids **Yes**, AI disclosure **Yes**
- [ ] Tara: hold Ep. 3+ until Ep. 1 clips confirm the characters render reliably

### Puppet route (parallel option — no credits, no drift)

- [x] Generate Tara's model sheet from the single prompt in `MODEL_SHEET_PROMPTS.md`
- [x] **Regenerate the A-pose full-frame** — braids behind the shoulders, empty
      hands, legs apart
- [ ] Regenerate two rejected expressions — curious came back in an orange top,
      surprised came back in a different render style
- [ ] Generate the other five sheets: Ravi, Chikoo, Kaaki, Nandu, Ammamma
- [x] Run `tools/autorig.py` on the A-pose and check `annotate()` output
- [x] Wire the PNGs into a rig — `tools/tara_photo_rig.py`
- [x] Check pivots with an all-zero-rotation frame — clean, no seams
- [ ] Split the arm at the elbow and the leg at the knee so the lantern can
      lift to chest height instead of swinging out sideways
- [ ] Generate background art to match the character — the coded scenes are now
      visibly the weakest part of the frame
- [ ] Decide the split: puppet for character performance, Flow for establishing shots

### Paused (Scout line — do not delete)

- [ ] Scout: generate Ep. 1 Flow clips (Block 1 → Block 2)
- [ ] Scout: generate Ep. 1 music, post-production and upload

---

## Notes / Blockers

_(Add anything that's stuck, half-done, or needs a decision here)_

---

## Recent Changes

| Date | Change |
|------|--------|
| 2026-08-13 | Created CLAUDE.md and ACTIVE_CONTEXT.md from handoff document |
| 2026-08-13 | Added FLOW_COMPLIANCE.md — Google Flow & Flow Music T&C prompt rules |
| 2026-08-13 | Updated CLAUDE.md — PR workflow rule, compliance section, YouTube AI disclosure steps |
| 2026-08-13 | Created ep01 shot blocks (28 shots, two-block split) and music prompt |
| 2026-08-13 | Music prompt updated to fast electro + vocal hook (BPM 132) |
| 2026-08-13 | Scout character description reordered — braids/boots first to avoid Sonic association in Flow |
| 2026-08-15 | New preschool series designed — character bible for Tara, Chikoo, Kaaki, Ammamma |
| 2026-08-15 | FLOW_COMPLIANCE §6 extended — IP safety checks for the Tara cast, plus preschool prompt rule barring realistic-human language |
| 2026-08-15 | Tara cast expanded to six (added Ravi, Nandu) and world/setting bible written; language layer deferred |
| 2026-08-15 | Tara series format doc written — seven-beat skeleton, three interactive beats, series music direction |
| 2026-08-15 | Tara Ep. 1 "Three Things for Ammamma" — 32-shot Flow block, VO script, trim guide, music prompt, metadata |
| 2026-08-15 | Tara made the channel's primary series; Scout line paused and preserved, not deleted |
| 2026-08-15 | Tara Ep. 2 "The Kite on the Wire" — 32 shots; Kaaki turns from taker into helper |
| 2026-08-15 | Character reference image prompts written for all six plus the lantern prop, with accept/reject checklists |
| 2026-08-15 | Added `tools/continuity_check.py` — automated frame-to-frame QC for Flow shots (jump/flicker/drift/freeze), validated against injected defects |
| 2026-08-15 | `tools/ANIMATION_APPROACH.md` — why frame-by-frame generation is not the method, and which parts of that workflow we do keep |
| 2026-08-15 | `series-tara/TEST_SHOT.md` — one 10-second clip to validate Tara before committing to 32 shots |
| 2026-08-15 | `tools/autorig.py` — cuts one A-pose image into rig parts; Nano Banana prompt sequence written |
| 2026-08-15 | Built a cut-out puppet engine — the technique Dora actually used. 12-part Tara rig, CALL-OUT PAUSE animated, 240 frames at 1080p rendered offline with no credits |
| 2026-08-15 | continuity_check JUMP now compares each frame to its local neighbourhood, so a real gesture in a still shot no longer reads as a discontinuity |
| 2026-08-15 | Puppet walk cycle added with a scrolling background — the cut-out technique for journeys; lantern resized after it dragged on the ground |
| 2026-08-15 | `series-tara/PART_SET_PROMPTS.md` — prompts for the real puppet artwork, flat-lit and pivot-aware |
| 2026-08-15 | Full no-Flow chain: four location stages, a camera, a second character rig, and multi-shot assembly in `tools/episode.py` |
| 2026-08-15 | One-prompt model sheets for all six cast — `series-tara/MODEL_SHEET_PROMPTS.md` |
| 2026-08-15 | Tara's first art generated: 19 images, character consistent across all of them; saved to `series-tara/reference/nano_banana_v1/` |
| 2026-08-15 | `autorig.load_rgba` rewritten to chroma-key magenta — the background came back as a gradient, which flat-colour keying cannot handle |
| 2026-08-15 | `tools/cut_strip.py` — six mouth shapes and four lantern stages cut to transparent PNGs from the real art |
| 2026-08-15 | Tara's A-pose regenerated correctly and cut into 6 rig parts; `tools/tara_photo_rig.py` builds her from the real artwork and the zero-rotation assembly is seamless |
| 2026-08-15 | CALL-OUT PAUSE re-rendered with the generated art, animation unchanged — the rig's art/performance split held |
| 2026-08-15 | autorig: arm crops no longer carry a full-height strip of tunic from the torso overlap |
| 2026-08-15 | `HANDOFF.md` written — project state, both production routes, hard-won lessons, open decisions |
| 2026-08-15 | `wave_hello()` — 5s greeting with anticipation and a decaying wave; gesturing arm moved in front of the torso so the shoulder joint stops opening |

---

## Scout Line — PAUSED (preserved for later)

## Episode 1 — "The Lost Map" Production Tracker

**Story:** Grimble steals Scout's Golden Explorer Map → Scout tracks him → instead of fighting, Scout draws Grimble onto the map → Grimble sees himself for the first time → rain cloud disappears, personal sunbeam appears → they walk home together.

**Runtime:** ~4:52 across 28 shots
**Music:** "The Lost Map" — cinematic adventure electronic, 2:40, no vocals

### Shot Generation

| Block | Shots | Status | Notes |
|-------|-------|--------|-------|
| Block 1 | 1–14 | ⬜ Not started | Paste `scout_adventure_v4_twoblock.md` Block 1 into Flow |
| Block 2 | 15–28 | ⬜ Not started | Paste Block 2 after Block 1 clips are done |

### Post-Production Steps

- [ ] Generate music track in Flow Music using prompt in `scout_adventure_v4.md`
- [ ] Concatenate all 28 clips with ffmpeg
- [ ] Merge music track
- [ ] Compress final video under 30MB
- [ ] Upload to YouTube
- [ ] Set title, description, thumbnail, AI disclosure, visibility

---

