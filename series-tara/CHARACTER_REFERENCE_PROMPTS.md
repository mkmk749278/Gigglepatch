# Tara Series — Character Reference Image Prompts

**Purpose:** generate the still reference images that get uploaded into the Flow
**Characters** tab. Flow holds a character far more consistently when it has an
image to anchor to, not just text — this is why `CLAUDE.md` already says to
upload a Scout reference image before every session.

**Where to run these:** Google ImageFX / Whisk / Imagen — same Google AI Pro
subscription as Flow, so nothing new to buy. Any image model works; these prompts
are not tool-specific.

---

## IMAGE PROMPTS ARE NOT VIDEO PROMPTS

A reference image has one job: show the character clearly so the model can lock
onto them. That means the opposite of a good video prompt.

| Reference images need | Never put in a reference prompt |
|---|---|
| Flat, even, neutral lighting | Volumetric light, god rays, rim light |
| Plain mid-grey background | Any environment, any scenery |
| Full body, feet visible, standing | Action poses, running, mid-jump |
| Straight-on framing | Camera angles, "low angle", "aerial" |
| Everything in focus | Depth of field, bokeh, shallow focus |
| Neutral, pleasant expression | Strong emotion (save that for the expression sheet) |

Anything cinematic in a reference image becomes baked-in noise that Flow then
tries to reproduce in every shot.

**The anti-drift ordering still applies.** Lead with the unique visual anchors,
never with role or nationality — same rule as the character bible.

---

## 1. TARA — primary reference (generate this one first)

```
Character reference sheet. Full body, standing straight, facing forward, arms
relaxed at sides, feet flat on the ground and fully visible. Plain flat mid-grey
background. Even neutral studio lighting, no strong shadows, everything in sharp
focus.

Two long black braids hanging down past the shoulders, each tied at the end with
a marigold-yellow ribbon. Holding a small brass star-shaped lantern with five
points in one hand by a ring handle. Wearing a teal-green cotton kurta tunic over
white churidar leggings, and scuffed red canvas shoes. A small dark bindi dot on
the forehead.

Warm brown skin, large dark-brown eyes, round full cheeks, gentle closed-mouth
smile. A young child of five — small, short, round-faced, clearly a little kid,
NOT a teenager, NOT an adult.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Stylised cartoon proportions with a slightly large head. NOT photorealistic, NOT
a real child, NOT live action, NOT flat 2D illustration, NOT anime.

IMPORTANT: hair is in two long braids with ribbons — NOT a short bob, NOT a
fringe across the forehead. She carries a star lantern — NOT a backpack. Full
body must be visible including both shoes.
```

### Accept / reject checklist

Generate **at least 8** and judge them against this. Do not settle early — every
future episode inherits whatever you pick.

**Reject immediately if:**
- Hair is a bob, or has a straight fringe across the forehead
- She is carrying a bag or backpack of any kind
- She reads as 8–12 years old rather than 5
- Clothing came out pink/orange instead of teal/white/red
- It looks photographic rather than animated
- The lantern is round, square, or lamp-shaped rather than a five-pointed star
- Feet or shoes are cropped out of frame

**Keep the one where:**
- Both braids and both ribbons are clearly visible
- The star lantern reads as a star at thumbnail size
- She looks five — round cheeks, short body, large head
- The face is warm and open, not blank

---

## 2. TARA — expression sheet (generate after the primary is locked)

Upload the chosen primary as a style reference first if the tool supports it.

```
Character expression sheet. Four head-and-shoulders portraits of the same young
girl character in a 2x2 grid, identical style and identical character in all four.
Plain flat mid-grey background. Even neutral lighting, everything in sharp focus.

Two long black braids with marigold-yellow ribbons, teal-green kurta collar
visible, small dark bindi on the forehead, warm brown skin, large dark-brown eyes,
round full cheeks. A child of five.

Top left: wide open delighted smile showing a gap in the front teeth.
Top right: curious, head tilted, eyebrows raised, asking a question.
Bottom left: thinking hard, eyes narrowed slightly, mouth to one side.
Bottom right: surprised, eyes wide, mouth a small round O.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Stylised cartoon proportions with a slightly large head. NOT photorealistic, NOT
a real child, NOT live action, NOT flat 2D.
```

The **curious / head tilted** expression is the one to get right — it is the
CALL-OUT PAUSE, and it appears three times in every single episode.

---

## 3. RAVI

```
Character reference sheet. Full body, standing straight, facing forward, hands
holding a cloth bag strap, feet flat on the ground and fully visible. Plain flat
mid-grey background. Even neutral studio lighting, no strong shadows, everything
in sharp focus.

Round black-rimmed glasses slightly too big for his face. A blue-and-white checked
cotton shirt buttoned all the way up, tucked into khaki shorts, with brown leather
sandals. Hair neatly oiled and combed flat with a side parting. A small cloth
shoulder bag worn across the body.

Warm brown skin, round face, slightly worried eyebrows, gentle closed-mouth smile.
A young child of five — small, short, round-faced, clearly a little kid, NOT a
teenager, NOT an adult.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Stylised cartoon proportions with a slightly large head. NOT photorealistic, NOT
a real child, NOT live action, NOT flat 2D illustration, NOT anime.

IMPORTANT: shirt is buttoned to the collar. Glasses are round and black. Full
body must be visible including both sandals.
```

**The critical test:** put Ravi's reference beside Tara's and shrink both to
thumbnail size. If you cannot instantly tell which is which, regenerate. Two
five-year-olds of similar build is the single most likely place this cast fails.

---

## 4. CHIKOO

```
Character reference sheet. Full body of a small squirrel, standing upright on hind
legs, side-on three-quarter view so the back is visible, tail up. Plain flat
mid-grey background. Even neutral lighting, everything in sharp focus.

Three pale cream stripes running down the back from head to tail. Small grey-brown
squirrel with a thin, very bushy upright tail almost as long as the body. Tiny
rounded ears, large glossy black eyes, small pink nose, cheek pouches. Palm-sized
and slim.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Real fur texture. NOT photorealistic, NOT flat 2D.

IMPORTANT: three cream stripes along the back must be clearly visible. Slim build
with a slender bushy tail — NOT a fat grey park squirrel, NOT a chipmunk with
stripes on its face, NOT wearing any clothing.
```

**Reject if** the stripes are on the face, the body is chubby and grey, or it is
wearing anything at all.

---

## 5. KAAKI

```
Character reference sheet. Full body of a plump crow standing on flat ground,
side-on three-quarter view, head turned toward the viewer. Plain flat mid-grey
background. Even neutral lighting, everything in sharp focus.

A grey collar of feathers around the neck and upper chest, against a glossy black
head, wings and tail. Plump rounded body with a head slightly too large for it.
Big round amber eyes with tiny pupils. Short stout grey-black beak. Three small
grey feathers on top of the head lying flat.

Cheerful, cheeky, comic expression — playful, never menacing, never scary, never
sinister. Bright friendly lighting.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Real feather texture. NOT photorealistic, NOT flat 2D.

IMPORTANT: grey neck collar against black body must be clearly visible. Rounded
and comic — NOT a sleek black raven, NOT gothic, NOT a horror crow, NOT sharp or
angular.
```

**Reject if** he looks sleek, sharp, dark-toned or in any way ominous. A
frightening antagonist would sink a preschool channel, and "crow" pulls hard in
that direction — expect to regenerate this one several times.

Generate a **second** reference with the head-feathers up:

```
Same crow character. Close-up head and shoulders, plain mid-grey background, even
lighting. The three small grey feathers on top of the head are standing straight
up and quivering. Big round amber eyes fixed on something below, cheeky mischievous
expression, beak slightly open. Comic and playful, never menacing.
```

That is THE FEATHER TELL, and it appears in every episode.

---

## 6. NANDU

```
Character reference sheet. Full body of a young water buffalo standing still,
side-on three-quarter view, all four legs visible on flat ground. Plain flat
mid-grey background. Even neutral lighting, everything in sharp focus.

Wide backswept crescent horns curving up and back from the head. Dark slate-grey
almost black hide with a sparse scatter of coarse hairs. Heavy barrel body on
short thick legs, broad flat muzzle, enormous dark eyes with long lashes, ears
held out sideways. A garland of small flowers looped over one horn. A smear of
dried mud on the flank.

Placid, sleepy, friendly, gentle expression.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Hide texture, physical weight. NOT photorealistic, NOT flat 2D.

IMPORTANT: crescent backswept horns and slate-grey hide — NOT a brown cow, NOT a
bull, NOT a bison, NOT aggressive, NOT charging, NOT lowering its head.
```

---

## 7. AMMAMMA

```
Character reference sheet. Full body, standing straight and upright, facing
forward, hands relaxed, feet visible. Plain flat mid-grey background. Even neutral
studio lighting, no strong shadows, everything in sharp focus.

Silver-grey hair pulled back into a low neat bun with a small white flower tucked
in at the side. Round wire-rimmed spectacles. A soft cotton sari in muted sage
green with a thin cream border, draped simply. Warm brown skin with deep laugh
lines around the eyes and mouth. Kind, alert, amused expression, gentle smile.

Standing easily and upright — active, capable and cheerful. NOT frail, NOT
stooped, NOT bent over, NOT sad, NOT using a stick.

3D CGI animated character, DreamWorks and Pixar theatrical animated film quality.
Fabric texture, physical weight. NOT photorealistic, NOT flat 2D.
```

**Reject if** she is stooped, leaning, or looks sad or tired. Expect to fight for
this one — "grandmother" pulls models toward frailty, which is exactly wrong for a
character whose job is confidently sending a child out of the house.

---

## 8. THE STAR LANTERN — prop reference

Worth generating on its own. It appears in close-up in every episode and must be
identical every time.

```
Product reference image of a single object on a plain flat mid-grey background.
Even neutral lighting, everything in sharp focus, no other objects in frame.

A small brass lantern in the shape of a five-pointed star, about the size of a
child's two hands. Aged warm brass with visible hammer marks. A small ring handle
at the top. Each of the five points contains a tiny separate light. All five
points are unlit and dark.

3D CGI animated style, DreamWorks and Pixar theatrical quality. NOT photorealistic.
```

Then a lit variant:

```
Same brass five-pointed star lantern, same plain mid-grey background and even
lighting. Exactly three of the five points glow with warm gold light. The other
two points are dark brass. The lit points cast a soft warm glow.
```

---

## WORKFLOW — the order that saves credits

1. **Tara primary.** Generate 8+, reject hard, pick one. Everything else is judged
   against her, so do not move on until she is right
2. **Tara expression sheet**, using the chosen primary as a style reference
3. **Ravi.** Then thumbnail-test him beside Tara — regenerate if they are not
   instantly distinguishable
4. **Chikoo, Kaaki, Nandu** — animals are far more forgiving, expect fewer attempts
5. **Kaaki feather-tell close-up**
6. **Ammamma**
7. **Star lantern**, unlit and lit
8. Only then upload all of it to the Flow **Characters** tab and start Episode 1

**Save every keeper** into `series-tara/reference/` with plain names —
`tara_primary.png`, `ravi_primary.png`, `kaaki_feathers_up.png`. Re-upload the same
files every Flow session forever. Regenerating references later means the
character silently changes between episodes, and children notice that faster than
adults do.

---

## SAFETY — applies to every prompt here

These are stylised animated characters, never depictions of real children. Per
`FLOW_COMPLIANCE.md` §6:

- Never remove the **NOT photorealistic / NOT a real child / NOT live action**
  clauses from the two child prompts
- Never write *realistic*, *photoreal*, *real child*, *live action*, *photograph*
  or *8K photo*
- Never upload a real child's photograph as a reference
- If a result comes back looking photographic rather than animated, **discard it**
