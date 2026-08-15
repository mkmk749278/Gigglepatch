# The 10-Second Test Shot

**Generate this before Episode 1.** One clip, ten seconds. It exists to answer a
single question: *does Tara survive ten seconds of motion?*

If she does, the 32-shot block is worth generating. If she does not, fixing it
here costs one clip instead of thirty-two.

---

## Why this particular action

The shot is: **walks a few steps → stops → turns to camera → lifts the lantern.**

That is not arbitrary. It stress-tests the four things every single episode
depends on, in one clip:

| What it tests | Why it is the risk |
|---|---|
| **Identity over time** | Ten seconds is long enough for a character to drift. Braids become loose hair, the kurta changes colour, her age creeps upward |
| **Hair in motion** | Two long braids are her primary anchor. If they cannot swing without tangling or vanishing, the whole design needs rethinking |
| **The lantern holds shape** | It must still read as a five-pointed star while being carried and lifted. Props deform badly under motion |
| **THE CALL-OUT PAUSE** | The turn-to-camera happens three times per episode, forever. If it does not work, the interactive format does not work |

A walk plus a turn plus a prop lift is also roughly the hardest thing this series
ever asks for. Everything else is easier.

---

## PROMPT — paste into Flow

Characters tab first: create **Tara** from `CHARACTER_BIBLE.md`, and upload her
locked reference image if you have one.

```
STYLE BIBLE: 3D CGI animated style, DreamWorks and Pixar theatrical animated
film quality. Glossy polished premium render. Large expressive eyes with bright
catchlights. Soft subsurface warmth in the skin. Crisp fabric detail. Physical
weight and personality-driven expressions. NOT photorealistic. NOT a real child.
NOT live action. NOT flat 2D illustration. Cinematic depth of field.
Volumetric lighting. Premium quality.

CHARACTER — TARA: girl of five, two long black braids each tied with a
marigold-yellow ribbon, teal-green cotton kurta over white churidar leggings,
scuffed red canvas shoes, small dark bindi, warm brown skin, large dark-brown
eyes, round full cheeks. Small and short — clearly a little kid. She carries a
small brass five-pointed star lantern by a ring handle in one hand.

SHOT — TEST: TARA WALKS AND TURNS
A sunlit dusty lane between two lime-washed compound walls, neem branches
overhead casting dappled light, early morning gold. Medium wide shot, camera
static at child height.

Tara walks toward the camera at an easy unhurried pace, three or four steps, the
brass star lantern swinging gently in her right hand. Her two long braids sway
with each step and the marigold-yellow ribbons bounce at the ends. Her red canvas
shoes scuff the dust.

She slows and stops. She turns to face the camera directly and looks straight
out. She lifts the brass star lantern up to chest height with both hands. She
tilts her head slightly and raises her eyebrows — curious, asking a question,
waiting for an answer. She holds still, smiling a warm gap-toothed smile.

Her clothing, hair, face and the lantern stay exactly the same throughout.
Gentle continuous motion. No cuts. No camera moves.
```

---

## What to check in the result

### 1. Run the continuity checker

```bash
python3 tools/continuity_check.py test_shot.mp4
```

Do this on the **raw** clip, before any grading. Anything reported as JUMP or
FLICKER means regenerate — do not try to fix it downstream.

### 2. Scrub it by eye

Pause at 0s, 3s, 6s and 9s and compare those four frames side by side:

| Check | Fail looks like |
|---|---|
| Same child at 0s and 9s? | Face subtly re-proportioned, age crept up |
| Both braids present throughout? | Braids merged, thinned, or became loose hair |
| Both ribbons still marigold-yellow? | Colour drifted, or a ribbon disappeared |
| Kurta still teal, leggings still white? | Palette slid — watch for orange or pink |
| Lantern still a five-pointed star? | Points melted into a blob or a round lamp |
| Does she look five at 9s? | Reads as 8–12 by the end |
| Feet in contact with the ground? | Sliding, floating, or the walk cycle skating |

### 3. Judge the turn specifically

The turn to camera is the money moment. Watch it three times. Ask:

- Does she look **at** the viewer, or past them?
- Does the head tilt read as *asking*, or just as tilting?
- Is the lantern lift smooth, or does it snap?
- Would a three-year-old understand they are being spoken to?

If the answer to the last one is no, that is a prompt problem, not a model
problem — push harder on "looks straight into the camera lens, directly at the
viewer, waiting for an answer."

---

## If it fails

Fix in this order, cheapest first:

1. **Regenerate with the same prompt.** Video models are stochastic — a second
   roll often just works
2. **Shorten to one action.** Drop the walk, keep only the turn and the lantern
   lift. Long multi-action clips drift far more than short single-action ones,
   and every shot in the episode is a single action anyway
3. **Add a start frame.** Give Flow the locked reference image as the opening
   frame so the character begins correct and only has to stay correct
4. **Strengthen the negatives.** If braids became loose hair, add *NOT loose
   flowing hair, NOT untied hair* at the very end of the prompt — Flow weights
   end-of-prompt negatives heavily
5. **Change the design.** If braids simply will not hold across ten seconds, that
   is worth knowing now, and the bible changes rather than the episode

---

## Only after this passes

- Generate the rest of the reference images
- Then the Episode 1 shot block
- Run `continuity_check.py` across all 32 shots before assembling anything
