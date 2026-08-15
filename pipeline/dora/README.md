# Dora — cutout animation pipeline

Renders finished shots of Dora from a single AI-generated plate. No GPU, no
video model, no per-run cost. CPU only.

```
python3 -c "import sys; sys.path.insert(0,'pipeline'); from dora import render; \
  render.render_shot('/tmp/frames', seconds=6.0); render.encode('/tmp/frames','out.mp4')"
```

---

## Why it is built this way

`ACTIVE_CONTEXT.md` records the finding that character consistency is
**architectural**: image models generate pixels and hold no character, so the
design drifts between generations. The Dora plate pack proves it — across 20
images the top changes colour, the lantern changes shape, and one head is flat
2D.

So exactly **one** plate is used: `assets/dora/plates/pose_walking.png`. It is
cut into bones and posed. The design cannot drift, because nothing is ever
re-generated.

---

## Modules

| File | Does |
|---|---|
| `key.py` | chroma key the magenta plates → RGBA, despill, cut the watermark |
| `rig.py` | split one plate into 14 bones, inpaint behind them, pose and composite |
| `anim.py` | gait plan, 2-bone IK, springs for hair and lantern, blink track |
| `face.py` | eyelids (the plate only has open eyes) |
| `scene.py` | procedural parallax night-market backdrop |
| `render.py` | camera, lantern light, shadows, motion blur, grain, encode |
| `inspect.py` | objective QC: motion energy, jerk, pop detection |

---

## The five things that make it read as animation, not as a moving cutout

1. **The feet are placed, not swung.** A leg on a sine wave moves fastest at
   mid-stance and stalls at the extremes, while the ground scrolls at a constant
   rate — that mismatch *is* foot skate. `ankle_path` moves the planted ankle
   **linearly** through stance and 2-bone IK solves the joints to match. Measured
   result: the ankle travels 14.0 px/frame against a 14.5 px/frame scroll.

2. **The pelvis height is derived.** The hip can only ride as high as the most
   extended stance leg allows. Solving for that produces the real two-per-cycle
   rise and fall for free, and guarantees the foot never sinks through the floor.

3. **Each bone owns a stub past its own joint, and its child draws on top.** A
   clean cut at the knee tears a wedge open the moment it bends. Overlap from
   both sides closes it.

4. **Nothing arrives at once.** Chest, head, braids and lantern lag the hips by
   different amounts. Braids and lantern are damped springs driven by their
   parent, so they overshoot and ring down.

5. **Motion blur is real.** The take is evaluated at 3× the output rate and the
   sub-frames inside the shutter are averaged.

---

## Traps hit while building this (do not re-discover)

| Symptom | Cause | Fix |
|---|---|---|
| Colour smears across the whole frame when a limb moves | nearest-colour inpaint grew into empty background | bound the fill to the plate silhouette |
| Legs turn dark teal and vanish | torso inpaint was baked into the torso, which draws *over* the legs | make the fill its own `backing` layer at the very back |
| Lantern loses its glow | part masks were decided on alpha > 0.5, so translucent pixels belonged to nobody | assign every soft pixel to the nearest solid owner |
| Braid renders as a brown smear | it was in the z-order *behind* the torso | braids drape over the kurta — draw them in front |
| Braid shreds when it swings | material test caught strands but not the gaps between them | morphological close + fill, then drop sub-400px components |
| Kurta hem swings away with the thigh | leg mask was "not cloth", and the shaded hem is not cloth-hued | leg mask is "unsaturated below the hem"; leg overlap may only reach leg pixels |
| Braid flies off screen | explicit spring integration goes unstable once `w·dt` approaches 2 | sub-step inside `spring` so the result is sample-rate independent |
| Legs fold up under her | IK solved against a world hip, but the legs hang off the torso, which is *also* offset | solve in the torso's local frame |
| Hard disc edge around the lantern | light falloff clipped linearly to zero at a finite radius | inverse-square falloff, no hard cutoff |
| Ground looks like video banding | cobble seams drawn as full-width horizontal lines | lay cobbles in rows that widen toward camera |

---

## Verifying a change

`rig.py` must be lossless at rest. Render the neutral pose and diff it against
the plate; mean absolute error is **0.0015** and should stay there. Anything
higher means a part is mis-assigned.

`inspect.report(frame_dir)` gives motion energy, jerk and pop frames. A walk
should show a smooth periodic energy curve with no isolated jerk spikes.
