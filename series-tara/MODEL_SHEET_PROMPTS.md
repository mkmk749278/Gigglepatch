# Tara Series — One-Prompt Model Sheets

Six prompts. One per character. Each produces a **complete model sheet in a
single generation** — hero pose, A-pose, turnaround, head views, expressions,
mouth shapes and props, all in one image, all in the same style because they came
out of the same pass.

This is the fast route. `NANO_BANANA_PROMPTS.md` holds the step-by-step version
(hero → edit → edit → edit), which gives finer control per panel. Use that one if
a sheet comes back inconsistent.

Compliance is unchanged: these are Google generative models under the terms in
`FLOW_COMPLIANCE.md`, output carries a SynthID watermark, and §2's ban on
realistic depictions of children applies. **Never remove the trailing NOT
clauses** — the stylised-animation clause is what makes a child character
compliant.

---

## WHAT THE FIRST RUN TAUGHT US

Tara's first sheet came back and is in `reference/nano_banana_v1/`. The character
itself is a keeper — consistent across nineteen images, correct palette, correct
props, premium render. Four things about the *A-pose panel specifically* need
fixing on the next pass, and all four are now written into the prompt above.

| What came back | Why it breaks the rig | Fix, now in the prompt |
|---|---|---|
| Braids hang forward over the chest, down past the elbows | The arm cut takes everything outside the torso columns between shoulder and hip — which is exactly where the braids are. The arms come out with a braid attached | **Both braids behind the shoulders**, down the back, out of the arm zone |
| The lantern is in her hand in every full-body shot | Same problem: it sits in the arm cut, so the hand and the prop become one rigid piece and the lantern can never be set down or lit | **Empty hands in the A-pose.** The lantern is a separate part — already cut, four stages, in `reference/parts/` |
| Legs touch from hip to ankle | Hip detection looks for the row where the central column splits in two. With the legs together it fires at the kurta hem instead | **Feet at least a shoe-width apart**, visible gap between the legs |
| A-pose only exists as a panel inside the sheet, a few hundred pixels tall | Not enough resolution to read limb runs from | Re-request it full-frame — see below |

Two things it got *better* than asked: it returned a **T-pose** rather than a
45-degree A-pose, which separates the arms even more cleanly and is fine to keep;
and the mouth strip and lantern strip came back clean enough to cut straight into
parts, which is done.

Also reject and regenerate two expression panels: the **curious** one came back
in an orange top instead of the teal kurta, and the **surprised** one is rendered
in a flatter, big-eyed style that does not match the rest. Both are kept in
`reference/nano_banana_v1/` with `_REJECT` in the filename so the failure mode
stays visible rather than being quietly deleted.

---

## THE FOLLOW-UP THAT IS NOT OPTIONAL

A twelve-panel sheet at one output resolution leaves each panel a few hundred
pixels tall. `tools/autorig.py` cuts limbs by reading runs of opaque pixels
across each scanline, so it needs the A-pose at real resolution. After every
human character's sheet, feed the sheet back in with:

```
From this exact character, generate the full-body A-pose alone as a single
full-frame image at maximum resolution, filling the frame from top to bottom.
Same character, same face, same hair, same clothes, same art style, same colours.

Standing straight, facing directly forward at the camera. Both arms held straight
out to the sides at about 45 degrees down from the shoulders, with a CLEAR WIDE
GAP between each arm and the body. BOTH HANDS COMPLETELY EMPTY — no lantern, no
props, nothing held. BOTH BRAIDS HANGING BEHIND THE SHOULDERS down her back, not
forward over the chest and not touching the arms. Feet flat on the ground at
least one shoe-width apart, with a CLEAR VISIBLE GAP between the legs from hip
to ankle.

Plain flat pure magenta background, one single even colour with no gradient,
nothing else in frame. Flat even lighting, no cast shadows, no ground shadow, no
rim light. Everything in sharp focus. No watermark, no signature, no logo, no
sparkle mark anywhere in the image.
```

Every capitalised clause in that prompt is there because the first run got it
wrong. Do not soften them.

### Why magenta

Magenta is chosen because **nothing on any of these characters is magenta** —
pick a colour that appears somewhere on the character and the cutter punches
holes in them. If the model can output true transparency instead, take that.

The first run confirmed why the colour matters more than the flatness. It came
back as a *gradient*, 205 to 241 across one frame, which is far outside any
tolerance tight enough to keep her black hair — so `autorig.load_rgba` no longer
measures distance from a sampled corner colour. It keys on `min(R, B) - G`
instead: the background sits near 150 on that measure while teal, skin, gold, red
shoes, black hair and white leggings all land at or below zero. Being a ratio
between channels, a brightness gradient barely moves it. The soft drop shadow
under her feet is still magenta, so it keys out too, and `largest_blob` removes
the model's corner sparkle watermark.

Ask for a flat background anyway — but the pipeline no longer depends on getting
one.

### Why the gaps in the A-pose

Arms flat against the sides leave no seam to cut along, and no amount of
cleverness invents one. The gap between arm and torso, and between the legs, is a
technical requirement, not a stylistic one.

---

## 1. TARA

```
Create an original character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same character in every panel.

THE CHARACTER
Two long black braids hanging down past the shoulders, each tied at the end with
a marigold-yellow ribbon. Carries a small brass star-shaped lantern with five
points, held in one hand by a ring handle. Wears a teal-green cotton kurta tunic
over white churidar leggings and scuffed red canvas shoes. A small dark bindi dot
on the forehead. Warm brown skin, large dark-brown eyes, round full cheeks, wide
open smile with a gap in the front teeth. A young child of five — small, short,
round-faced, clearly a little kid, NOT a teenager and NOT an adult. Bright,
curious, confident posture.

PANELS
1. Full body hero pose, three-quarter view, standing confidently, lantern raised
   to chest height, smiling at the camera.
2. Full body A-POSE, standing straight, facing directly forward at the camera,
   both arms held out and down at about 45 degrees from the body with a CLEAR
   VISIBLE GAP between each arm and the torso, legs straight and slightly apart
   with a CLEAR VISIBLE GAP between them, arms straight, palms forward. Whole
   body visible from the top of the head to below both shoes.
3. Full body BACK VIEW, standing straight, arms down, both braids visible.
4. Head and neck only, front view, facing straight forward, neutral gentle smile.
5. Head and neck only, three-quarter view, head turned about 30 degrees to her
   left, eyes toward the camera.
6. Head and neck only, profile view, head turned 90 degrees to her left.
7. Head only — CURIOUS: head tilted to one side, eyebrows raised, eyes wide and
   looking directly at the camera, mouth in a small open smile as if asking a
   question and waiting for an answer.
8. Head only — DELIGHTED: wide gap-toothed grin, eyes crinkled shut with joy.
9. Head only — THINKING: eyes narrowed slightly, looking up and to one side,
   mouth pushed to one side.
10. Head only — SURPRISED: eyes very wide, eyebrows high, mouth a small round O.
11. A row of six mouth shapes only, no face around them, same lip colour:
    closed gentle smile / small round O / wide open smile showing lower teeth /
    wide oval singing / slightly open relaxed / broad grin with a gap in the
    front teeth.
12. The star lantern prop alone, shown four times in a row with 0, 1, 2 and 3 of
    its five points glowing warm gold, the rest dark brass.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render. Large expressive eyes with bright catchlights
and visible iris detail. Soft subsurface warmth in the skin with gentle cheek
blush. Crisp fabric detail with visible weave. Stylised cartoon proportions with
a slightly large head.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders, no drop shadows anywhere in the image.

NOT photorealistic. NOT a real child. NOT live action. NOT flat 2D illustration.
NOT anime.

Important: her hair is in two long braids with ribbons — NOT a short bob and NOT
a fringe across the forehead. She carries a star lantern, NOT a backpack. She
wears teal and white — NOT orange trousers, NOT a pink top.
```

**Panel 7 is the one to judge the sheet on.** That is THE CALL-OUT PAUSE, and it
appears three times in every episode.

---

## 2. RAVI

Generate Tara first. Ravi is checked *against* her.

```
Create an original character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same character in every panel.

THE CHARACTER
Round black-rimmed glasses slightly too big for his face. A blue-and-white
checked cotton shirt buttoned all the way up, tucked into khaki shorts, with
brown leather sandals. Hair neatly oiled and combed flat with a side parting.
Carries a small cloth shoulder bag across the body. Warm brown skin, round face,
slightly worried eyebrows that lift when he is excited. A young child of five —
small, short, round-faced, clearly a little kid, NOT a teenager and NOT an adult.
Careful, thoughtful posture.

PANELS
1. Full body hero pose, three-quarter view, standing with one hand on the bag
   strap, looking at the camera.
2. Full body A-POSE, standing straight, facing directly forward at the camera,
   both arms held out and down at about 45 degrees from the body with a CLEAR
   VISIBLE GAP between each arm and the torso, legs straight and slightly apart
   with a CLEAR VISIBLE GAP between them, arms straight, palms forward. The
   shoulder bag strap must not bridge the gap between arm and body. Whole body
   visible from the top of the head to below both sandals.
3. Full body BACK VIEW, standing straight, arms down.
4. Head and neck only, front view, facing straight forward, neutral expression.
5. Head and neck only, three-quarter view, head turned about 30 degrees to his
   left, eyes toward the camera.
6. Head and neck only, profile view, head turned 90 degrees to his left.
7. Head only — UNSURE: eyebrows pulled together and up, mouth small and pressed,
   eyes looking slightly sideways.
8. Head only — THE IDEA: eyebrows high, eyes bright and wide behind the glasses,
   mouth open in a small delighted O, one finger pushing the glasses up his nose.
9. Head only — PLEASED: warm closed-mouth smile, eyes relaxed.
10. Head only — WORRIED: eyebrows steeply raised in the middle, mouth turned
    down slightly.
11. A row of six mouth shapes only, no face around them, same lip colour:
    closed neutral / small round O / open smile showing lower teeth / wide oval
    singing / slightly open relaxed / pressed-together worried line.
12. This character standing at full body beside a five-year-old girl character
    with two long black braids tied with marigold-yellow ribbons, a teal-green
    kurta over white leggings, red canvas shoes, holding a small brass
    five-pointed star lantern — both children full body, side by side, to show
    they read as two clearly different children.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render. Large expressive eyes with bright catchlights
and visible iris detail. Soft subsurface warmth in the skin with gentle cheek
blush. Crisp fabric detail with visible weave. Stylised cartoon proportions with
a slightly large head.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders, no drop shadows anywhere in the image.

NOT photorealistic. NOT a real child. NOT live action. NOT flat 2D illustration.
NOT anime.

Important: round glasses and a buttoned checked shirt — he is a careful,
thoughtful child, visibly different from the girl with braids.
```

**Shrink panel 12 to thumbnail size and look at it.** Two five-year-olds of
similar build is where this cast is most likely to fail. If you cannot tell them
apart instantly at that size, regenerate — the glasses and the checked shirt are
the silhouette-level reads that have to carry it.

---

## 3. CHIKOO

No A-pose — Chikoo rigs from three parts, so a clean side view with the tail
clear of the body is all the cutter needs.

```
Create an original animal character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same creature in every panel.

THE CHARACTER
Three pale cream stripes running down the back from head to tail. A small
grey-brown squirrel with a thin, very bushy upright tail almost as long as the
body. Tiny rounded ears, large glossy black eyes, small pink nose, cheek pouches
that visibly bulge when full. Palm-sized — small enough to sit on a child's
shoulder. Quick, twitchy, alert.

PANELS
1. Full body SIDE VIEW, sitting upright on his haunches, front paws held
   together at the chest, tail arcing up behind him with a CLEAR VISIBLE GAP
   between the tail and the body along its whole length.
2. Full body side view, on all fours, mid-scamper, tail streaming behind.
3. Full body front view, sitting upright, facing the camera.
4. Full body BACK VIEW, showing all three cream stripes clearly.
5. Head only, three-quarter view, alert and bright-eyed.
6. Head only, cheek pouches bulging full, mouth busy.
7. Head only, scared — eyes very wide, ears flattened back.
8. Head only, delighted — eyes crinkled, mouth open in a chitter.
9. The tail alone, shown three times: hanging relaxed / raised upright and
   bushy / curled over at the top into a clear question-mark hook.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render, real fur texture, physical weight, large
expressive eyes with bright catchlights, personality-driven expressions.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders anywhere in the image.

NOT photorealistic. NOT flat 2D illustration.

Important: three cream stripes along the back are always visible. Slim build with
a slender bushy tail — NOT a fat grey park squirrel, NOT a chipmunk with facial
stripes. No boots, no clothing, no upright human posture.
```

Panel 9's question-mark hook is THE TAIL QUESTION — the show's wordless way of
asking the viewer something, for the end of the audience too young to follow
speech.

---

## 4. KAAKI

```
Create an original animal character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same creature in every panel.

THE CHARACTER
A grey collar of feathers around the neck and upper chest, against a glossy black
head, wings and tail. Plump rounded body with a head slightly too large for it,
giving a comic look. Big round amber eyes with tiny pupils. Short stout grey-black
beak. Three small grey feathers on top of the head that lie flat most of the time.
Cheerful, cheeky, mischievous expression — playful and comic, never menacing,
never scary, never sinister.

PANELS
1. Full body SIDE VIEW, standing, wings folded against the body, head-feathers
   lying flat.
2. Full body side view, wings spread wide mid-flap, with a CLEAR VISIBLE GAP
   between each wing and the body.
3. Full body front view, standing, facing the camera.
4. Full body side view, mid-hop, one foot lifted.
5. Head only, side view, head-feathers lying flat, calm.
6. Head only, side view, THE FEATHER TELL — the three grey head-feathers
   standing straight up and quivering, eyes fixed sideways on something, beak
   slightly open, scheming.
7. Head only, front view, startled — eyes very wide, beak open in a squawk.
8. Head only, three-quarter view, pleased and cheeky.
9. One wing alone, shown twice: folded, and fully spread.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render, real feather texture, physical weight, large
expressive eyes with bright catchlights, personality-driven expressions. Bright
friendly daytime colours.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders anywhere in the image.

NOT photorealistic. NOT flat 2D illustration.

Important: the grey neck collar against the black body is always visible.
Rounded and comic — NOT a sleek black raven, NOT gothic, NOT a horror crow, NOT
menacing.
```

"Crow" pulls hard toward gothic and Halloween. The grey collar leads for a
reason, and the four separate non-menacing cues before the render block are all
load-bearing — a frightening antagonist ends a preschool channel.

---

## 5. NANDU

```
Create an original animal character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same creature in every panel.

THE CHARACTER
Wide backswept crescent horns curving up and back from the head. Dark slate-grey
almost black hide with a sparse scatter of coarse hairs. Heavy barrel body on
short thick legs, broad flat muzzle, enormous dark eyes with long lashes, ears
held out sideways. A young water buffalo — big and heavy but soft-faced and calm.
Placid, sleepy, friendly. A smear of dried mud on one flank and a garland of
small orange flowers looped over one horn.

PANELS
1. Full body SIDE VIEW, standing square, all four legs visible with a CLEAR
   VISIBLE GAP between the front pair and the rear pair.
2. Full body three-quarter view, standing, head turned slightly toward the
   camera.
3. Full body front view, standing, facing the camera head-on.
4. Full body side view, lying down comfortably with legs folded under.
5. Head only, side view, calm and sleepy, eyes half closed.
6. Head only, front view, eyes wide open and friendly, ears out.
7. Head only, three-quarter view, chewing, mouth working sideways.
8. Head only, mildly surprised — ears forward, eyes open wide, still gentle.
9. The flower garland alone, and one horn alone, side by side.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render, hide texture, real physical weight, large
expressive eyes with bright catchlights and long lashes, personality-driven
expressions.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders anywhere in the image.

NOT photorealistic. NOT flat 2D illustration.

Important: crescent backswept horns and slate-grey hide — NOT a brown cow, NOT a
bull, NOT an American bison. NOT aggressive, NOT charging, NOT snorting. Calm and
gentle in every panel.
```

He is the obstacle that is not a threat — he blocks Neem Lane purely by existing
and having no intention of moving. Any panel that reads as angry is a reject.

---

## 6. AMMAMMA

```
Create an original character model sheet for a preschool animated series.
Produce ONE image containing all of the following panels, arranged in a clean
grid, all on the SAME flat pure magenta background (#FF00FF), all in exactly the
same art style, same colours and the same character in every panel.

THE CHARACTER
Silver-grey hair pulled back into a low neat bun with a small white flower tucked
in at the side. Round wire-rimmed spectacles. Wears a soft cotton sari in muted
sage green with a thin cream border, draped simply. Warm brown skin with deep
laugh lines around the eyes and mouth. Kind, alert, amused expression. Stands and
moves easily and upright — an active, capable older woman, a grandmother.

PANELS
1. Full body hero pose, three-quarter view, standing upright and relaxed, one
   hand gesturing as if explaining something.
2. Full body A-POSE, standing straight, facing directly forward at the camera,
   both arms held out and down at about 45 degrees from the body with a CLEAR
   VISIBLE GAP between each arm and the torso, feet slightly apart. The sari
   drape must not bridge the gap between arm and body. Whole body visible from
   the top of the head to below the feet.
3. Full body side view, standing upright.
4. Head and neck only, front view, facing straight forward, warm neutral
   expression.
5. Head and neck only, three-quarter view, head turned about 30 degrees to her
   left.
6. Head and neck only, profile view, head turned 90 degrees to her left.
7. Head only — WARM: a broad affectionate smile, eyes crinkled with laugh lines.
8. Head only — EXPLAINING: eyebrows raised, mouth mid-word, alert and clear.
9. Head only — AMUSED: one eyebrow slightly higher, knowing half-smile.
10. A row of six mouth shapes only, no face around them, same lip colour:
    closed gentle smile / small round O / open smile showing teeth / wide oval /
    slightly open relaxed / broad warm grin.

RENDER
Premium 3D CGI animated feature film character, DreamWorks and Pixar theatrical
quality. Glossy polished render. Large expressive eyes with bright catchlights.
Soft subsurface warmth in the skin. Crisp fabric detail with visible cotton
weave in the sari. Stylised cartoon proportions.

FLAT EVEN LIGHTING on every panel — no cast shadows, no shading direction, no
rim light, no ground shadows. Everything in sharp focus. No text, no labels, no
numbers, no borders anywhere in the image.

NOT photorealistic. NOT a real person. NOT live action. NOT flat 2D illustration.

Important: she is upright, active and cheerful — NOT frail, NOT bent, NOT stooped,
NOT sad, NOT using a stick.
```

The triple negative at the end is doing real work. "Old woman" pulls the model
toward frailty and stooping, and this character has to be someone who sends a
child off confidently — not someone the child is worrying about.

---

## GENERATE IN THIS ORDER

1. **Tara**, alone, until she is right. Everything else is judged against her
2. **Ravi**, then check panel 12 at thumbnail size
3. **Chikoo**, **Kaaki**, **Nandu**
4. **Ammamma**

No group or crowd shots until all six sheets are locked.

---

## AFTER GENERATING

Save the sheets and the full-resolution A-poses into `series-tara/reference/`:

```
tara_sheet.png       tara_apose.png
ravi_sheet.png       ravi_apose.png
chikoo_sheet.png     kaaki_sheet.png       nandu_sheet.png
ammamma_sheet.png    ammamma_apose.png
```

Strips of small objects — the mouth shapes, the lantern stages — go through
`cut_strip.py` instead, which keys and separates them without any silhouette
analysis:

```bash
python3 tools/cut_strip.py series-tara/reference/nano_banana_v1/tara_mouths.jpeg \
                           series-tara/reference/parts mouth 6
python3 tools/cut_strip.py series-tara/reference/nano_banana_v1/tara_lantern_stages.jpeg \
                           series-tara/reference/parts lantern 4
```

Both are already done and committed — six mouths and four lantern stages are in
`series-tara/reference/parts/`.

Then cut the A-pose and check the joints before building anything on them:

```bash
python3 tools/autorig.py series-tara/reference/tara_apose.png \
                        series-tara/reference/parts/

python3 -c "import sys; sys.path.insert(0,'tools'); from autorig import annotate; \
            annotate('series-tara/reference/tara_apose.png','check.jpg')"
```

Open `check.jpg`. The lines mark neck, shoulder, hip and the torso columns. If any
of them sits in the wrong place the cut will be wrong, and the usual cause is a
pose problem — arms too close to the body, or something bridging the gap between
arm and torso.

---

## REJECT A SHEET IF

- Any panel looks photographic rather than animated → discard, do not push it
  further (`FLOW_COMPLIANCE.md` §2, and the Safety Position in
  `CHARACTER_BIBLE.md`)
- The character changes between panels — different face, different shade of
  teal, different number of braids
- Shadows are baked into the artwork. The rig rotates limbs; a shadow cast to
  one side will point the wrong way in every frame of every episode
- The background is not flat, or the character wears the background colour
  anywhere
- Tara has a bob, a fringe, a backpack, or orange trousers
- Ravi is indistinguishable from Tara at thumbnail size
