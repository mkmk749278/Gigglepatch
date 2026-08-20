#!/usr/bin/env python3
"""
Generate shot plates from a hosted image model.

Procedural Blender geometry tops out at a flat-shaded look no amount of
lighting work fixes. Pollinations serves a diffusion model with no API key and
no account, so plates come from there instead and the CPU here is spent on
animating them.

Prompts share one style prefix so all fifteen plates read as one film, and each
asks explicitly for foreground / midground / background separation -- the
compositor's parallax is driven by estimated depth, and a flat composition
animates like a sliding card.
"""
import os, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env

W, H = 1024, 576   # the service caps here; larger requests are downscaled
BASE = 'https://image.pollinations.ai/prompt/'

STYLE = ("3D render, DreamWorks animation style, stylized cartoon, "
         "high detail, sharp focus, deep perspective, cinematic")
NEG = "text, watermark, logo, signature, blurry, flat lighting, low detail"

# Subject first, style last, kept short. Long prompts made the model fixate on
# a single object and drop the composition entirely.
SHOTS = {
    '01_approach': "narrow dirt road at night leaving a small sleeping village, curving into dark pine forest, one glowing amber lantern on a post, stars, ground mist",
    '02_lanterns': "looking up a forest road at night, huge ancient trees arching overhead into a tunnel, amber lanterns hanging from branches receding into darkness, roots and wet leaves",
    '03_canopy':   "upward view through dense dark pine branches framing a starry night sky, silhouetted foliage, crescent moon, hanging paper lanterns among the branches",
    '04_deep':     "deep night forest, long strings of glowing amber lanterns hung between tall tree trunks receding far into blue mist, layered depth",
    '05_turn':     "between two enormous dark tree trunks, warm amber glow spilling from the middle distance lighting the mist from within, cold dark forest around",

    '06_gate':     "tall arched gateway of woven branches hung with glowing lanterns, opening onto a market lane at night, striped awnings receding both sides",
    '07_stalls_l': "night market stall close up, rows of hand blown glass jars on worn wooden shelves each holding a different colored glowing light, rich reflections",
    '08_stalls_r': "night market stall counter close up, rolled parchment maps, leather journals and brass instruments on weathered wood, one hanging lantern, deep shadow",
    '09_lane':     "long night market lane, wooden stalls both sides with colorful striped awnings receding into distance, glowing amber lanterns strung overhead, misty depth",
    '10_awnings':  "looking up at a night market canopy, overlapping striped awnings, tangled rope, clustered glowing lanterns of many sizes against the night sky",

    '11_clearing': "grassy forest clearing at night ringed by tall dark pine trees, a worn stone path entering from the foreground, moonlight, fireflies, low mist",
    '12_door_wide':"a single tall carved stone doorway standing alone in an open moonlit clearing, no walls, the opening glowing bright teal cyan, amber lanterns far behind in the trees",
    '13_door_close':"close on a weathered carved stone doorway standing alone, moss in the crevices, teal cyan light spilling across wet grass and mist, warm amber rim light behind",
    '14_leave':    "looking back down a forest path from beside a glowing doorway, clearing in front, small distant warm amber market glow far behind, teal light from the right edge",

    '15_title':    "wide high viewpoint over a glowing lantern lit market village in a forest valley at night, hundreds of warm lights, mist between the trees, mountains behind, starry sky",
}


def url_for(prompt, seed):
    full = f'{prompt}, {STYLE}'
    q = urllib.parse.quote(full, safe='')
    return (f'{BASE}{q}?width={W}&height={H}&nologo=true&model=flux'
            f'&seed={seed}&negative={urllib.parse.quote(NEG, safe="")}')


def fetch(name, prompt, seed, outdir, tries=4):
    dest = os.path.join(outdir, f'{name}.jpg')
    if os.path.exists(dest) and os.path.getsize(dest) > 20000:
        return 'have'
    for a in range(tries):
        try:
            req = urllib.request.Request(url_for(prompt, seed),
                                         headers={'User-Agent': 'gigglepatch/1.0'})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = r.read()
            if len(data) < 20000:
                raise ValueError(f'suspiciously small ({len(data)}B)')
            with open(dest, 'wb') as f:
                f.write(data)
            return f'{len(data)//1024}KB'
        except Exception as e:
            if a == tries - 1:
                return f'FAIL {type(e).__name__}: {str(e)[:70]}'
            time.sleep(4 * (a + 1))


def main():
    outdir = os.path.join(env.SP, 'genplates')
    os.makedirs(outdir, exist_ok=True)
    only = sys.argv[1:] or list(SHOTS)
    t0 = time.time()
    for i, name in enumerate(only):
        if name not in SHOTS:
            continue
        r = fetch(name, SHOTS[name], 4400 + i * 13, outdir)
        print(f'  {name:14s} {r}', flush=True)
    print(f'\ndone in {(time.time()-t0)/60:.1f} min -> {outdir}')


if __name__ == '__main__':
    main()
