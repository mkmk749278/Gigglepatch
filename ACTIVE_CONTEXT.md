# GigglePatch — Active Context
### Last updated: 2026-08-15

> Update this file whenever something changes. It is the single source of truth for what is happening right now.

---

## Current Status

**Phase:** Production route resolved for character shots — a working CPU animation
pipeline now renders finished footage from a single plate.
**Immediate priority:** Review `renders/dora_lantern_walk.mp4`, then decide the
Dora naming question (see Blockers) before any publish.

### Dora — cutout pipeline (new, working)

A full shot pipeline lives in `pipeline/dora/`. It cuts **one** approved plate
into a 14-bone puppet and animates it, so the design cannot drift between
frames. It needs no GPU and no video model.

What it produces: 1280x720 / 24fps, real motion blur, procedural parallax
night-market backdrop, the star lantern lighting the scene and the street.

Why it works where earlier attempts did not — the walk is *solved*, not swung:
the planted ankle is moved linearly through stance and 2-bone IK derives the
joints, so foot travel matches ground scroll (measured 14.0 vs 14.5 px/frame)
and the skating that killed the earlier 2.5D tests is gone.

Full notes and the trap list: `pipeline/dora/README.md`.

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
| **Bone-rigged cutout from one plate** | **perfect** | **high — keeps the plate's render quality** | **in use for Dora; single camera angle per plate** |

Negative results worth remembering:
- Flux **cannot** produce a consistent multi-angle turnaround — it ignores angle
  instructions and drifts the design. There is no image-gen path to 360.
- Single-image 3D (TripoSR) on a stylized character produces unusable geometry.

---

## Production Route Decision (open)

| Route | Needs | Gets |
|-------|-------|------|
| Keep Google Flow | nothing | best motion quality; consistency via Characters tab |
| Video API (Replicate/FAL) | API key | Claude generates directly, no setup |
| **GPU PC + Claude Code locally** | 24GB VRAM GPU | LoRA training + local video models, no per-run cost |
| CC0 rigged 3D | nothing | guaranteed consistency, low-poly look |

**Note:** this cloud sandbox has no GPU and blocks SSH, so it cannot drive a rented
GPU box. Running Claude Code *on* the GPU machine is the way to use one.

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
- ⚠️ **Dora's name is not cleared.** The visual design is original and safe; the
  *name* collides with a well-known children's-TV explorer character. Rename
  before publish — no art needs to change. See `FLOW_COMPLIANCE.md` §6.
- The cutout pipeline animates one plate, so each plate gives one camera angle.
  New angles need new approved plates, keyed and rigged the same way.

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
| 2026-08-15 | Dora plate pack received (20 images), keyed to RGBA in `assets/dora/plates/` |
| 2026-08-15 | Built `pipeline/dora/` — bone-rigged cutout animation, CPU only |
| 2026-08-15 | First finished shot rendered: `renders/dora_lantern_walk.mp4` |
| 2026-08-15 | Flagged Dora naming risk in FLOW_COMPLIANCE.md |
