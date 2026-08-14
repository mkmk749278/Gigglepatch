# GigglePatch Animation Pipeline

Everything here is **CPU code** — it runs anywhere. On a GPU machine it runs the
same, just faster, and sits alongside the GPU-only steps (video diffusion, LoRA
training) that this environment could not do.

---

## Why this exists

The recurring problem across every approach was **character consistency**.
The root cause is architectural, not a prompting failure:

> AI image and video models generate **pixels**. They hold no persistent model of
> a character, so every generation is an independent guess and the design drifts.
> Games and Pixar have perfect consistency because the character is a **persistent
> asset** that is posed and re-rendered, never re-imagined.

Everything below is organised around that fact.

---

## Layout

```
pipeline/
  rig/          2.5D cutout rigs — one artwork, posed per frame
    kiran_rig.py    front-facing rig (head/arms/legs/blink/lipsync)
    side_rig.py     side profile, single-segment legs
    side_rig2.py    side profile, 2-bone IK legs  ← the good one
  vfx/
    door_fx.py      animated magic-door compositor (trace → erupt → open)
  scene3d/
    render_fox.py   CC0 rigged fox, Blender/Cycles, 360 orbit
    forest_scene.py forest environment assembly + scattering
    turntable.py    software mesh renderer (no GPU, no OpenGL)
  assets/
    gen_keyframes.py / fix_keyframes.py   Flux plate generation
  build_v2.py       full episode build (rig + plates + VFX + audio)
  showcase.py       character motion test (blur, IK, overlap)
```

---

## Environment notes (hard-won)

| Problem | Fix |
|---|---|
| System `ffmpeg` broken (`libcaca.so.0`) | `imageio_ffmpeg.get_ffmpeg_exe()` ships a static binary |
| All HTTPS needs the proxy CA | `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt` |
| Blender EEVEE fails headless | needs `libEGL`; use **Cycles** (CPU, no OpenGL) |
| `sc.render.engine='CYCLES'` rejected | enable the addon **and set the engine in the same process** — the enum caches at import |
| `minterpolate` outputs nothing | needs **≥3 source frames**; synthesize a blended midpoint |
| `zoompan` on video input explodes | use `d=1` (`d=N` emits N frames *per input frame*) |
| TripoSR: no `torchmcubes` | patch to `skimage.measure.marching_cubes` |
| TripoSR: state-dict key mismatch | `transformers<5` (v5 renamed ViT layers) |
| Quaternius FBX imports near-black | restate materials by name (Wood/Green/DarkGreen/...) |
| Fox rig is ~20x the nature assets | normalise every asset to a real-world height |

---

## Animation principles implemented (`rig/side_rig2.py`)

These are the things that separate "moving" from "alive":

- **2-bone IK legs** — the foot is *pinned to the ground* through stance and the
  hip/knee angles are solved backwards (law of cosines). Feet cannot skate.
- **Overlapping action** — hips lead; chest lags 2 frames, head 3.5, ears 5,
  tail 6.5. Nothing moves in unison.
- **Ease curves** instead of raw sine — nothing moves at constant velocity.
- **Ankle roll** — boot stays level on the ground, rolls through toe-off.
- **Weight shift + squash/stretch** on impact.
- **Motion blur** — sub-frame sampling, averaged (`render_blurred`).

Ground travel is always matched to stride length:
`distance_per_cycle = stride / stance_fraction`

---

## Free CC0 assets in use

| Source | License | Contents |
|---|---|---|
| **Quaternius** Ultimate Animated Animals | **CC0** | Fox, Wolf, Deer, Stag, Husky, Shiba, Horse, Cow, Bull, Donkey, Alpaca — each with 12 animations (Walk, Gallop, Idle ×4, Jump, Attack, Eating…) |
| **Quaternius** Ultimate Nature | **CC0** | 129 assets: trees, bushes, rocks, grass, flowers, stumps |
| **Blender** asset bundles | CC0 | Human base meshes |

CC0 = public domain. Commercial use, no attribution required.

---

## On a GPU machine — what unlocks

Not possible in the CPU sandbox this was built in:

1. **Character LoRA training** — the real consistency fix. Train once on ~30–50
   images; the model then *knows* the character across every generation.
2. **Local video diffusion** — Wan 2.2, HunyuanVideo, LTX-Video, CogVideoX.
   Needs **24GB VRAM** for the good ones.
3. **GPU Blender rendering** — Cycles CPU here was ~12s/frame at 960×540;
   expect well under 1s on a 4090.

Recommended flow once a GPU is available:
`LoRA-locked character images → image-to-video → assemble/voice/score with the
CPU tooling in this repo.`
