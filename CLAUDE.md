# GigglePatch — Claude Project Reference

This repo stores production files for the GigglePatch YouTube channel (@Gigglepatch7492).
All video is AI-generated on mobile using Google Flow + Flow Music + ffmpeg. No computer required.

---

## Channel

- **Name:** GigglePatch
- **Handle:** @Gigglepatch7492
- **URL:** https://www.youtube.com/channel/UCPn8z0XQ2ykv3Rt_Oexn9wQ
- **Content mix:** *Tara and the Star Lantern* — interactive preschool series (primary) + kids songs (broad reach). Scout adventures are paused
- **Cadence:** 1 new video per week minimum

---

## Production Stack

```
Google Flow (labs.google/fx)   → AI video clips (8–10 sec each)
Flow Music (Lyria model)       → Instrumental music tracks
ffmpeg (mobile)                → Concatenate clips, merge music, compress under 30MB
```

---

## Primary Series — Tara and the Star Lantern

Interactive preschool, Made for Kids: **Yes**. This is the channel's main line.

- Cast, world and Flow anti-drift descriptions: `series-tara/CHARACTER_BIBLE.md`
- Episode skeleton and interactive rules: `series-tara/SERIES_FORMAT.md`
- Episodes: `series-tara/ep*/`

**Cast:** Tara (5, lead) · Ravi (5, friend) · Chikoo (palm squirrel) ·
Kaaki (crow, the taker) · Nandu (water buffalo) · Ammamma (grandmother)

**Never in a Tara prompt:** *realistic*, *photoreal*, *real child*, *live
action*, *photograph*. These are stylised animated characters. See
`FLOW_COMPLIANCE.md` §6.

---

## Characters — Scout line (PAUSED)

> Scout and Grimble are not in active production. Episode 1 "The Lost Map" is
> written and unstarted in `episodes/ep01-the-lost-map/`. Everything below is
> preserved for when it resumes. Do not delete.

### Scout (hero)

**Flow Characters tab — paste this description (order matters: lead with braids and boots, not species):**

> Explorer and adventurer. Long braided dreadlocks — thick genuine loc braids decorated with teal-blue beads and burnt-orange beads woven along their length. Orange-brown leather hiking boots on both feet — rugged, worn-in explorer boots. Bare paws, no gloves. Cream-colored fur patch on his chest. Anthropomorphic hedgehog character. Blue fur. Brown expressive eyes. Athletic build — natural proportions, not baby-round, not hulking. Warm, curious, confident posture. 3D CGI animated style. DreamWorks/Pixar theatrical quality. Physical weight, fur texture, personality-driven expressions. NOT photorealistic. NOT flat 2D. IMPORTANT: Character has braided dreadlocks hanging down — NOT swept-back pointed quills. Boots are always visible on both feet.

**Why this order:** Starting with "braided dreadlocks" and "hiking boots" anchors Flow on Scout's unique features before it reads "blue hedgehog" — which otherwise triggers Sonic associations from training data.

**Copyright safety:** braided locs + hiking boots + explorer identity = legally distinct from any existing IP. No white gloves, no swept-back quills, no speedster identity.

**Visual signatures (use by name in every shot prompt):**

| Signature | When | What happens |
|-----------|------|-------------|
| THE BOOT PRINT TRAIL | Scout runs | Glowing golden boot-sole impressions appear behind him, 3–4 visible, each fades after 2 sec |
| THE EXPLORER PULSE | Brave decision | Warm golden compass-rose ring expands from chest, fades at arm's length, one pulse only |
| THE DISCOVERY GLOW | Breakthrough | Teal+orange beads pulse in sequence (teal-orange-teal-orange); 3–4 tiny golden sparkles drift up from braid tips |

### Grimble (villain)

Large round dark-purple storm cloud creature. Grumpy downturned mouth set into cloud mass. Two narrow glowing white eyes. Wiggly dark tentacle arms. Purple electricity at edges. Small personal rain cloud above him, rains only on him in a tiny vertical column.

| State | Rain | Lightning |
|-------|------|-----------|
| Angry | Heavy | Jagged purple |
| Calming | Lightens | Softens to rounded sparks |
| Happy | Rain cloud vanishes → tiny personal sunbeam | — |

---

## Google Flow Rules

1. **Characters tab first, always** — upload Scout reference image + paste character description before generating any shots each session.
2. **Style Bible at top of every prompt block:**
   > STYLE BIBLE: 3D CGI animated style, DreamWorks and Pixar theatrical animated film quality. Characters have physical weight, real fur texture, personality-driven expressions and proportions. NOT photorealistic. NOT flat 2D illustration. Cinematic depth of field in wide shots. Volumetric lighting throughout. Premium quality every shot.
3. **All shots in one block** (or two max). Never paste shots one at a time — Flow uses the full block as context.

**Sky color language:**
- Bright blue = Scout's world (safe, exploring)
- Deep purple = Grimble's world (stormy, lonely)
- Soft pink = Grimble beginning to change
- Full rainbow = complete transformation, joy

---

## Color Language

| Color | Meaning |
|-------|---------|
| Bright blue sky | Scout's world — safe, warm, exploring |
| Deep purple sky | Grimble's world — stormy, closed, lonely |
| Soft pink sky | Grimble beginning to change |
| Full rainbow | Full transformation — joy unlocked |
| Golden glow | Explorer Map — memory, discovery, warmth |
| Amber-gold ring | Explorer Pulse — courage, true north |
| Teal + orange beads | Discovery Glow — breakthrough moment |

---

## Flow Music Rules

Always specify:
- "No voiceover. No lyrics. Purely instrumental."
- "General audience — not a baby show."
- BPM and mood arc
- Time-coded structure matching story beats

---

## YouTube Upload Checklist

Before every publish:

- [ ] Title — clean, no technical filenames
- [ ] Description — character intro + subscribe CTA + hashtags
- [ ] Thumbnail — brightest, clearest frame
- [ ] Made for Kids — Yes (kids songs) / No (Scout episodes)
- [ ] **AI disclosure toggle** — YouTube Studio → "Altered or synthetic content" → Yes (required by YouTube policy)
- [ ] **AI disclosure in description** — add line: `✨ Created using Google Flow (AI video) and Flow Music/Lyria (AI music). All characters are original and fictional.`
- [ ] Visibility — Public
- [ ] Shorts remixing — Allow

**Title formula:** `[What happens] 🎵 | [Song/Episode type] | GigglePatch`

**Description formula:**
```
[1-line hook]

[1-line call to action]

🔔 Subscribe to GigglePatch for new episodes every week!

#GigglePatch #[ContentTag] #[GenreTag] #[AudienceTag]
```

---

## Repository Workflow (Claude Instructions)

1. **Always work on a feature branch** — never commit directly to main.
2. **Open a PR for every change** — even single-file updates.
3. **Merge after green CI** — if CI checks exist, wait for them to pass before merging. If there are no CI checks, merge immediately after the PR is opened.
4. **Update ACTIVE_CONTEXT.md** on every PR — reflect the current production status before pushing.
5. **Compliance check before writing prompts** — every new video or music prompt must follow `FLOW_COMPLIANCE.md`. Never reference existing IP, real people, or copyrighted works by name.

---

## Prompt Compliance

Before writing any Flow video or Flow Music prompt, check `FLOW_COMPLIANCE.md`.

Quick rules:
- Describe Scout and Grimble by visual attributes only — never name any existing character or IP
- No real people, no copyrighted logos, no branded assets in any prompt
- Music: describe mood and instruments — never reference a specific song or artist by name
- Always include "No voiceover. No lyrics. Purely instrumental." in every music prompt
- Always disclose AI use on YouTube (required by platform policy)

---

## Repository Structure

```
CLAUDE.md                          ← this file (project reference for Claude)
ACTIVE_CONTEXT.md                  ← current production status (update constantly)
FLOW_COMPLIANCE.md                 ← Google Flow & Flow Music T&C rules for prompts
series-tara/                       ← PRIMARY SERIES
  CHARACTER_BIBLE.md               ← cast, world, Flow anti-drift descriptions
  SERIES_FORMAT.md                 ← episode skeleton, interactive rules
  ep01-three-things/
    tara_ep01.md                   ← 32-shot block + VO script + music + metadata
  ep02-kite-on-the-wire/
    tara_ep02.md
episodes/                          ← Scout line (PAUSED)
  ep01-the-lost-map/
    scout_adventure_v4.md          ← full 28-shot Flow prompt block + metadata
    scout_adventure_v4_twoblock.md ← same episode split into two blocks
```
