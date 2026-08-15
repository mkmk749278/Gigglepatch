# Tara — Puppet Part Set

Prompts for generating the character art the cut-out rig needs. Each piece is
generated separately, on a transparent background, and dropped into
`series-tara/reference/parts/`.

This is the front-loaded cost of the puppet route. Once these exist, every
episode is free forever and the character can never drift.

---

## THE RULE THAT MATTERS MOST

**Flat, even lighting. No shadows. No shading direction. No background.**

The rig supplies motion, and motion changes which way a limb faces. Any shadow
baked into the artwork will point the wrong way the moment the part rotates, and
it will do so in every frame of every episode. A shadow under the chin is fine —
it rotates with the head. A shadow cast to the left across the torso is not.

Add lighting later, over the whole composited frame, where it can be consistent.

---

## HOW A PART IS BUILT

Every part needs one thing beyond the artwork: **a pivot**, the point it rotates
around. Generate the piece with a little clear space around that end so the joint
does not clip when it swings.

| Part | Pivot sits at | Leave clear space at |
|---|---|---|
| head | base of the neck | below the chin |
| upper arm | shoulder | the shoulder end |
| forearm + hand | elbow | the elbow end |
| thigh | hip | the hip end |
| shin + shoe | knee | the knee end |
| braid | where it leaves the head | the top |

Overlap matters too — a forearm should be drawn slightly longer at the elbow than
it looks, so that when it bends there is no gap at the joint.

---

## 1. HEAD — front view

```
A single character head, front view, facing straight forward. Isolated on a
fully transparent background, nothing else in frame.

A young girl of five. Round full cheeks, warm brown skin, large dark-brown eyes
with bright catchlights, small dark bindi on the forehead, black hair parted in
the centre and pulled back. Gentle closed-mouth smile. Neck included below the
chin.

Flat even lighting, no cast shadows, no shading direction, no rim light, no
background, no ground shadow. Clean edges. Stylised 3D CGI animated character,
DreamWorks and Pixar quality, slightly large head proportions. NOT
photorealistic, NOT a real child, NOT live action, NOT flat 2D line art.

Head and neck only. No body, no shoulders.
```

Also generate: **three-quarter view** and **profile**, same prompt with the view
changed. A cut-out rig swaps head art rather than rotating it in 3D, so a
character who only ever faces front cannot look at anything.

## 2. MOUTH SHAPES

```
A set of six mouth shapes for a cartoon child character, arranged in a row on a
fully transparent background. Same style and same lip colour in all six.

1: closed gentle smile
2: small round O
3: wide open smile showing lower teeth
4: wide oval, singing
5: slight open, relaxed
6: broad grin with a gap in the front teeth

Mouths only — no face, no skin, nothing around them. Flat even lighting, no
shadows, no background.
```

Six is the working minimum for readable speech. Swap them per frame against the
head; the rig treats the mouth as a child of the head, so it rides along.

## 3. TORSO

```
The torso of a young girl's outfit, front view, isolated on a fully transparent
background. Nothing else in frame.

A teal-green cotton kurta tunic, plain, with short sleeves ending at the upper
arm. Slight fabric weave visible. The neck opening at the top, the hem at the
bottom. No arms, no head, no legs.

Flat even lighting, no cast shadows, no shading direction, no background.
Stylised 3D CGI animated style, DreamWorks and Pixar quality. NOT
photorealistic, NOT flat 2D.
```

## 4. UPPER ARM · FOREARM AND HAND

```
A single upper arm of a child's teal-green kurta sleeve, isolated on a fully
transparent background. Straight, seen from the front, shoulder end at the top
and elbow end at the bottom. Rounded at both ends. Nothing else in frame.

Flat even lighting, no cast shadows, no background. Stylised 3D CGI animated
style. NOT photorealistic, NOT flat 2D.
```

```
A single child's forearm and open hand, warm brown skin, isolated on a fully
transparent background. Straight, seen from the front, elbow end at the top and
the hand at the bottom. Fingers together, relaxed and slightly curled, as if
about to hold something. Nothing else in frame.

Flat even lighting, no cast shadows, no background. Stylised 3D CGI animated
style. NOT photorealistic, NOT flat 2D.
```

Also generate a **gripping hand** variant — fingers closed around an implied
handle — for the lantern.

## 5. THIGH · SHIN AND SHOE

```
A single child's thigh in white churidar leggings, isolated on a fully
transparent background. Straight, front view, hip end at the top and knee at the
bottom, rounded at both ends. Nothing else in frame.

Flat even lighting, no cast shadows, no background. Stylised 3D CGI animated
style. NOT photorealistic, NOT flat 2D.
```

```
A single child's lower leg in white churidar leggings ending in a scuffed red
canvas shoe, isolated on a fully transparent background. Straight, front view,
knee at the top and the shoe at the bottom. Nothing else in frame.

Flat even lighting, no cast shadows, no background. Stylised 3D CGI animated
style. NOT photorealistic, NOT flat 2D.
```

## 6. BRAID

```
A single long black plaited braid, isolated on a fully transparent background.
Hanging straight down, the plait pattern visible along its length, tied at the
bottom end with a marigold-yellow ribbon in a small bow. The top end is where it
joins the head. Nothing else in frame.

Flat even lighting, no cast shadows, no background. Stylised 3D CGI animated
style. NOT photorealistic, NOT flat 2D.
```

One is enough — the rig mirrors it for the other side.

## 7. THE STAR LANTERN

```
A small brass lantern shaped like a five-pointed star, isolated on a fully
transparent background, hanging from a small ring handle at the top. Aged warm
brass with visible hammer marks. Each of the five points holds a tiny light, all
five unlit and dark. Nothing else in frame, no background, no ground shadow.

Flat even lighting. Stylised 3D CGI animated style, DreamWorks and Pixar
quality. NOT photorealistic.
```

Generate four variants — **0, 1, 2 and 3 points lit** — so THE STAR COUNT can
simply swap art as the journey progresses.

**Scale it against the torso.** The first placeholder was drawn far too large and
dragged along the ground during the walk; a lantern a five-year-old carries is
roughly half the height of her torso, no more.

---

## FILE LAYOUT

```
series-tara/reference/parts/
    head_front.png        head_3q.png        head_profile.png
    mouths.png            (six shapes in a row, cut in code)
    torso.png
    upper_arm.png         forearm_hand.png   hand_grip.png
    thigh.png             shin_shoe.png
    braid.png
    lantern_0.png  lantern_1.png  lantern_2.png  lantern_3.png
```

---

## WIRING THEM IN

In `tools/tara_rig.py`, each `_draw_*` function currently returns
`(image, pivot)`. Replace the body with a load:

```python
def _draw_head():
    im = Image.open('series-tara/reference/parts/head_front.png').convert('RGBA')
    return im, (im.width // 2, int(im.height * 0.86))   # pivot at the neck
```

Then adjust the `attach` points in `build_rig` until the joints line up. Nothing
in `call_out_pause()` or `walk_cycle()` changes — the animation is written
against part names and angles, not against artwork.

**Check the pivots before animating.** Render a single frame with every rotation
at zero and confirm the character stands correctly assembled. A pivot that is
ten pixels off looks fine standing still and tears the joint open the moment the
limb swings.

---

## WHAT THIS BUYS

| | |
|---|---|
| Character consistency | Perfect, permanently — the art never changes |
| Cost per episode after this | Zero |
| Render time | ~70 seconds per 10-second shot at 1080p |
| Policy risk | None |
| Works offline | Yes |

The two proof clips in the repo — the CALL-OUT PAUSE and the walk cycle — were
both rendered from placeholder art through exactly this pipeline. Swapping in
real art changes how they look and nothing about how they work.
