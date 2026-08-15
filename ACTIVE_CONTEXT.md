# GigglePatch — Active Context
### Last updated: 2026-08-15

> Update this file whenever something changes. It is the single source of truth for what is happening right now.

---

## Current Status

**Phase:** Two content lines running in parallel
**Immediate priority:** Generate Flow clips for "The Lost Map" (Scout vs. Grimble, Ep. 1)
**New:** Second series in design — *Tara and the Star Lantern*, interactive preschool

### Content lines

| Line | Audience | Made for Kids | Status |
|------|----------|---------------|--------|
| Kids songs | Broad | Yes | 2 uploaded |
| Scout adventures | General audience | **No** | Ep. 1 in production |
| Tara (preschool) | Ages 2–5 | **Yes** | Characters designed |

Scout's positioning is unchanged — general audience, "not a baby show." Tara is
a separate line and the two never share an episode.

---

## Videos

| # | Title | Type | Made for Kids | Status |
|---|-------|------|---------------|--------|
| 1 | Down on the Farm 🐓 | Farm animal song | Yes | ✅ Uploaded |
| 2 | Five Little Dinosaurs 🦕 | Dino dance song | Yes | ✅ Uploaded |
| 3 | The Lost Map — Scout vs. GRIMBLE | Adventure episode | No | 🎬 In production |

---

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

## Flow Session Checklist (run at the start of every Flow session)

- [ ] Open Characters tab
- [ ] Upload Scout reference image
- [ ] Paste Scout character description
- [ ] Save character
- [ ] Then paste shot block

---

## Next Episodes (ideas queue)

| Priority | Idea | Notes |
|----------|------|-------|
| Next | Scout finds a hidden underwater cave | Introduces water world |
| After | Grimble tries to help Scout cross a desert | Grimble's first useful moment |
| Later | Scout discovers Rainbow Hill's secret | What makes the hill striped |

---

## Tara Series — Design Tracker

**Format:** Interactive preschool — direct address, pause-for-answer, three-stop journey
**Cast:** Tara (lead) · Ravi (friend) · Chikoo (palm squirrel) · Kaaki (crow, the taker) · Nandu (water buffalo) · Ammamma (grandmother)
**World:** Small town at the edge of fields — Blue Door House, Banyan Court, Neem Lane, Stepwell, Mango Grove, Water Tank, Rooftops, Market Lane
**Device:** Five-point brass star lantern — three points light per episode, one per stop

| Item | Status |
|------|--------|
| Character bible | ✅ `series-tara/CHARACTER_BIBLE.md` |
| IP safety documented in FLOW_COMPLIANCE §6 | ✅ Done |
| Series format doc | ✅ `series-tara/SERIES_FORMAT.md` |
| Episode 1 shot block | ✅ `series-tara/ep01-three-things/tara_ep01.md` (32 shots) |
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

- [ ] Generate Episode 1 Flow clips (Block 1 → Block 2)
- [ ] Generate Episode 1 music
- [ ] Complete Episode 1 post-production and upload
- [ ] Plan Episode 2 prompt blocks
- [ ] Tara: generate Ep. 1 Flow clips (Tara alone first, then the rest)
- [ ] Tara: decide voice route, then record/synthesise the VO track
- [ ] Tara: generate Ep. 1 music (BPM 96 acoustic prompt)

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
