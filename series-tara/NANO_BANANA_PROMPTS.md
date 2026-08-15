# Tara — Nano Banana (Gemini 2.5 Flash Image) Prompts

**Why this model over ImageFX for our use:** it holds a character across
generations and accepts editing instructions on an image it already made. A
cut-out rig needs the *same* character in several poses and views, which is
precisely the thing that is hard to get out of a one-shot text-to-image tool.

Compliance is unchanged — it is a Google generative model under the same terms
as Flow and ImageFX, and its output carries the same SynthID watermark. All the
rules in `FLOW_COMPLIANCE.md` still apply, including the ban on realistic
depictions of children. Keep every "stylised, NOT photorealistic" clause.

---

## THE ORDER MATTERS

Work in this sequence and lean on the model's consistency, rather than
describing her from scratch each time:

1. **Hero image** — get Tara right once, at full quality. Nothing else proceeds
   until this one is right
2. **A-pose** — same character, re-posed. This is the one the rig needs
3. **Head views** — same character, turned
4. **Expressions** — same head, different face

Steps 2 to 4 are *edits of step 1*, not new generations. That is the whole point
of using this model.

**Want it in one paste instead?** `MODEL_SHEET_PROMPTS.md` has a single
all-in-one prompt per character that produces the whole sheet — hero, A-pose,
turnaround, head views, expressions, mouths and props — in one generation, for
all six of the cast. It is faster and the panels are guaranteed to match each
other because they came out of the same pass. Come back here when a sheet returns
inconsistent and you need per-panel control.

---

## STEP 1 — THE HERO IMAGE

```
Create an original character for a preschool animated series.

A five-year-old girl. Two long black braids hanging past her shoulders, each
tied at the end with a marigold-yellow ribbon. She wears a teal-green cotton
kurta tunic over white churidar leggings and scuffed red canvas shoes. A small
dark bindi on her forehead. Warm brown skin, large dark-brown eyes, round full
cheeks, a wide open smile with a gap in her front teeth. She carries a small
brass lantern shaped like a five-pointed star, held by a ring handle in one hand.

She is small, short and round-faced — clearly a little kid, not a teenager.
Bright, curious, confident posture.

Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render. Large expressive eyes with bright catchlights
and visible iris detail. Soft subsurface warmth in the skin with gentle cheek
blush. Crisp fabric detail with visible weave. Stylised cartoon proportions with
a slightly large head.

NOT photorealistic. NOT a real child. NOT live action. NOT flat 2D illustration.
NOT anime.

Important: her hair is in two long braids with ribbons — not a short bob and not
a fringe across the forehead. She carries a star lantern, not a backpack. She
wears teal and white — not orange trousers, not a pink top.
```

Generate several. Judge against the checklist in
`CHARACTER_REFERENCE_PROMPTS.md` and do not settle — everything downstream
inherits this choice.

---

## STEP 2 — THE A-POSE (what the rig actually needs)

Feed the chosen hero image back in with this:

```
Keep this exact character — same face, same braids, same ribbons, same teal
kurta, same white leggings, same red shoes, same star lantern, same art style
and same colours. Change only her pose and the background.

Full body, standing straight, facing directly forward at the camera.
A-pose: both arms held out and down at about 45 degrees from her body, with a
clear visible gap between each arm and her torso. Legs straight and slightly
apart with a clear visible gap between them. Arms straight, palms forward.

Plain solid pure magenta background, flat single colour, nothing else in frame,
no ground shadow, no props except the lantern in her hand.

Flat even lighting across the whole figure. No cast shadows, no strong shading
direction, no rim light. Everything in sharp focus. Full body visible from the
top of her head to below both shoes, with space around the edges.
```

### Why magenta

The auto-cutter removes a flat background by sampling the corners. Magenta is
chosen because **nothing on Tara is magenta** — pick a colour that appears
nowhere on the character or the cutter will punch holes in her. If the model can
output true transparency instead, take that.

### Why the gaps matter

`tools/autorig.py` finds limbs by looking for separate runs of opaque pixels
across each scanline. Arms flat against the sides leave no seam to cut along.
The gaps are not an aesthetic choice — without them the cut cannot be made.

---

## STEP 3 — HEAD VIEWS

A cut-out rig swaps head artwork rather than rotating it in 3D, so a character
who only ever faces front can never look at anything.

```
Keep this exact character — same face, same braids, same ribbons, same colours,
same art style. Show only her head and neck, nothing below the shoulders.

Three-quarter view, her head turned about 30 degrees to her left, eyes looking
toward the camera. Plain solid pure magenta background, flat even lighting, no
shadows, everything in sharp focus.
```

Repeat with **"profile view, her head turned 90 degrees to her left"**.

---

## STEP 4 — EXPRESSIONS

```
Keep this exact character and this exact head angle — same face, same braids,
same colours, same art style. Change only her expression.

Curious and questioning: head tilted slightly to one side, eyebrows raised,
eyes wide and looking directly at the camera, mouth in a small open smile as if
asking a question and waiting for an answer.

Plain solid pure magenta background, flat even lighting, no shadows.
```

Then repeat for: **delighted** (wide gap-toothed grin, eyes crinkled),
**thinking** (eyes narrowed slightly, mouth to one side), and **surprised**
(eyes wide, mouth a small round O).

The **curious/questioning** one matters most — it is the CALL-OUT PAUSE, and it
appears three times in every episode.

---

## AFTER GENERATING

```bash
# cut the A-pose into rig parts
python3 tools/autorig.py tara_apose.png series-tara/reference/parts/

# check the detected joints before building anything on them
python3 -c "import sys; sys.path.insert(0,'tools'); from autorig import annotate; \
            annotate('tara_apose.png','check.jpg')"
```

Open `check.jpg`. The lines mark neck, shoulder, hip and the torso columns. If
any of them sits in the wrong place the cut will be wrong, and the usual cause
is a pose problem — arms too close to the body, or a prop bridging the gap
between arm and torso.

Save the keepers as:

```
series-tara/reference/
    tara_hero.png            tara_apose.png
    tara_head_front.png      tara_head_3q.png       tara_head_profile.png
    tara_expr_curious.png    tara_expr_delighted.png
    tara_expr_thinking.png   tara_expr_surprised.png
```

Then send me `tara_apose.png` and I will cut it, wire it into the rig, and
re-render the walk cycle and the call-out with real art.

---

## THE SAME FOR THE REST OF THE CAST

Once Tara works, the identical four-step sequence covers Ravi, Kaaki, Nandu and
Ammamma — descriptions are in `CHARACTER_BIBLE.md`. Two notes:

- **Ravi must be thumbnail-distinguishable from Tara.** Generate him, shrink both
  to thumbnail size side by side, and regenerate if you cannot tell them apart
  instantly. Two five-year-olds of similar build is where this cast is most
  likely to fail
- **The animals do not need an A-pose.** Chikoo and Kaaki are rigged from three
  or four parts, so a clean side view with the tail and wings clear of the body
  is enough
