# GigglePatch — Active Context
### Last updated: 2026-08-20

> Update this file whenever something changes. It is the single source of truth for what is happening right now.

---

## Current Status

**Phase:** Evaluating production methods — character design NOT finalized, testing what
gives reliable character consistency for adventure episodes
**Immediate priority:** Decide the production route (see "Production Route Decision" below)

### Key finding from method testing

Character consistency is an **architectural** problem, not a prompting problem:
AI image/video models generate pixels and hold no persistent character, so the design
drifts between generations. Games and Pixar are consistent because the character is a
**persistent asset** that is posed and re-rendered.

Methods tested (all code in `pipeline/`, notes in `pipeline/README.md`):

| Method | Consistency | Visual quality | Verdict |
|--------|-------------|----------------|---------|
| Flow clips + Ken Burns | poor between clips | high | motion too static |
| Programmatic 2D (PIL) | perfect | very low | rejected — looks dated |
| Flux plates + interpolation + coded VFX | good | high | usable; motion is the limit |
| 2.5D cutout rig (IK, overlap, motion blur) | **perfect** | medium | only 2 fixed angles possible |
| Image→3D (TripoSR, CPU) | n/a | unusable | single-image 3D gives a blob |
| **CC0 rigged 3D + Blender** | **perfect** | medium (low-poly) | **true 360, real mocap** |

Negative results worth remembering:
- Flux **cannot** produce a consistent multi-angle turnaround — it ignores angle
  instructions and drifts the design. There is no image-gen path to 360.
- Single-image 3D (TripoSR) on a stylized character produces unusable geometry.

---

## Production Route Decision — RESOLVED (2026-08-20)

**Constraint confirmed by the user: there is no GPU machine and no budget.**
Everything must run in the cloud sandbox (4 CPU cores, 15 GB RAM, no GPU,
ephemeral container) plus web access. That rules out every route except the
CPU pipeline, so the decision is made by elimination:

| Route | Status |
|---|---|
| Google Flow | Needs AI Pro tier + credits; cost scales with clip count, so long-form is not free |
| Video API (Replicate/FAL) | Paid per second of output |
| GPU PC + local models | No GPU available |
| **CPU pipeline (this repo)** | **Chosen — zero marginal cost, unlimited length** |

### Measured on this container (2026-08-20)

| Stage | Throughput | 10-min episode |
|---|---|---|
| 2.5D rig, no motion blur | 0.88 s/frame | ~55 min on 4 cores |
| 2.5D rig, 4x motion blur | 3.88 s/frame | ~4 h on 4 cores |
| Blender Cycles CPU (960x540, 32 spp) | 8.47 s/frame | ~8.5 h on 4 cores |
| Kokoro TTS | 0.72x realtime | ~7 min |

**Architecture that makes long-form affordable:** Blender renders character and
background *plates* once (minutes of compute), then the 2.5D rig animates those
plates at ~0.9 s/frame. Rendering full 3D per frame is ~10x more expensive and
is not used for episode-length work.

**Accepted trade-off:** this route cannot hit the DreamWorks/Pixar look the
CLAUDE.md style bible describes. It is low-poly CC0 plus 2.5D cutout animation
— "medium" quality by our own method testing. That is the unavoidable cost of
free-with-no-GPU, and it is the only route that produces long videos at zero
marginal cost.

**Open:** episode-length renders exceed the container's idle lifetime, so long
builds must render in committed chunks rather than one pass.

---

## Pipeline reproducibility — FIXED (2026-08-20)

All 13 pipeline scripts hardcoded an absolute path into a *previous session's*
scratchpad, and the assets they loaded were never committed. The pipeline had
been unrunnable since that container was reclaimed.

- `pipeline/env.py` — repo-relative path resolution (`SP`, `ASSETS`, `KF`)
- `pipeline/fetch_assets.py` — re-downloads the Kokoro TTS model on a fresh container
- `pipeline/smoke_test.py` — verifies all 7 stages; currently **7/7 passing**
- `.gitignore` — keeps the 337 MB asset cache and render intermediates out of git

**Still missing:** the source artwork (`kiran_side.png`, the Flux keyframe
plates) was lost with the old container and cannot be regenerated on CPU. The
smoke test runs against a synthetic placeholder plate. Regenerating real plates
needs either the Flow account or a Blender-rendered character.

---

## Videos

| # | Title | Type | Made for Kids | Status |
|---|-------|------|---------------|--------|
| 1 | Down on the Farm 🐓 | Farm animal song | Yes | ✅ Uploaded |
| 2 | Five Little Dinosaurs 🦕 | Dino dance song | Yes | ✅ Uploaded |
| 3 | The Lost Map — Scout | Adventure episode | No | ⏸ Shelved — replaced by Midnight Market |

---

## Active Series: The Midnight Market

**Concept:** Mystery + hidden magic adventure for ages 6–12. A young fox named Kiran is the only one who can see hidden doors that appear at midnight, leading to a vast secret bazaar where folklore creatures come to trade.

**Series bible:** `episodes/the-midnight-market/` (see artifact link in chat history)

### Characters — CONFIRMED ✅

All three characters generated and approved in Google Flow. Reference images saved to repo.

| Character | File | Status |
|-----------|------|--------|
| Kiran (protagonist) | `characters/kiran_reference.jpg` | ✅ Confirmed |
| Chimki (guide) | `characters/chimki_reference.jpg` | ✅ Confirmed |
| The Collector (antagonist) | `characters/collector_reference.jpg` | ✅ Confirmed |

Flow Characters tab descriptions: `characters/character_descriptions.md`

### Episode 1 — "The First Door"

| Step | Status | Notes |
|------|--------|-------|
| Episode concept | ✅ Done | See series bible |
| Character references | ✅ Done | All three saved in repo |
| Shot block (28 shots) | ✅ Done | `ep01-the-first-door-shotblock.md` — two-block split, paste-ready |
| Flow clip generation | ⬜ Not started | Paste Block 1 then Block 2 into Flow |
| Music prompt | ✅ Done | In shot block file — cinematic adventure electronic, BPM 97 |
| Post-production | ⬜ Not started | ffmpeg concat + compress |
| YouTube upload | ⬜ Not started | — |

---

## Flow Session Checklist (run at the start of every Flow session)

- [ ] Open Characters tab
- [ ] Upload `kiran_reference.jpg` → paste Kiran description → Save
- [ ] Upload `chimki_reference.jpg` → paste Chimki description → Save
- [ ] Upload `collector_reference.jpg` → paste Collector description → Save
- [ ] Then paste shot block (Style Bible at top)

---

## Series Episode Queue

| # | Episode | Status |
|---|---------|--------|
| 1 | "The First Door" — Kiran discovers the Market, meets Chimki | ⬜ Shot block needed |
| 2 | "The Shop of Lost Things" — first sighting of the Collector | ⬜ Planned |
| 3 | "The Storm Singer" — Keeper speaks for the first time | ⬜ Planned |
| 4 | "The Collector's Name" — antagonist moves to foreground | ⬜ Planned |
| 5 | "The Book That Refused to Stay" — vetala folk tale | ⬜ Planned |

---

## Open Tasks

- [x] Write Episode 1 shot block (28 shots, two-block split for Flow) — `ep01-the-first-door-shotblock.md`
- [x] Write Episode 1 music prompt — in shot block file, cinematic adventure electronic, BPM 97
- [ ] Generate Episode 1 Flow clips — paste Block 1 then Block 2 into Flow
- [ ] Complete Episode 1 post-production and upload
- [ ] Continue kids songs in parallel (2–3/week for watch hours growth)

---

## Notes / Blockers

- Scout / "The Lost Map" shelved — replaced by The Midnight Market (stronger market positioning for 6–12 audience)
- Flow character references confirmed — use these every session, do not regenerate from scratch
- Chimki came out as a translucent crystal mouse with starlight inside — better than original concept, keep this design

---

## Recent Changes

| Date | Change |
|------|--------|
| 2026-08-13 | Created CLAUDE.md and ACTIVE_CONTEXT.md from handoff document |
| 2026-08-13 | Added FLOW_COMPLIANCE.md — Google Flow & Flow Music T&C prompt rules |
| 2026-08-13 | Updated CLAUDE.md — PR workflow rule, compliance section, YouTube AI disclosure steps |
| 2026-08-13 | Created ep01 shot blocks (28 shots, two-block split) and music prompt for The First Door |
| 2026-08-13 | Scout / The Lost Map shelved — strategic pivot to The Midnight Market |
| 2026-08-13 | Series bible created for The Midnight Market (mystery + hidden magic, ages 6–12) |
| 2026-08-13 | All three character reference images generated in Google Flow and confirmed |
| 2026-08-13 | Character descriptions saved to episodes/the-midnight-market/characters/ |
