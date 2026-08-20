#!/usr/bin/env python3
"""
Stage 1 — Generate Flux keyframes for Midnight Market Ep01 teaser.
Same seed locks character + environment consistency.
Prompt deltas create pose/framing progression for motion interpolation.
"""
import requests, urllib.parse, os, time, random
from concurrent.futures import ThreadPoolExecutor

CA  = '/root/.ccr/ca-bundle.crt'
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != '/' and not _os.path.exists(_os.path.join(_d, 'env.py')):
    _d = _os.path.dirname(_d)
_sys.path.insert(0, _d)
from env import KF as OUT
os.makedirs(OUT, exist_ok=True)

STYLE = ('Pixar DreamWorks 3D animation style, cinematic lighting, depth of field, '
         'high detail, volumetric light, 3D animated movie screenshot')

# Locked character formula (variant E — validated)
FOX = ('a fox character child {ACT}, dressed in a navy pocket jacket and brown boots, '
       'standing upright on two legs, orange furred fox head with snout and pointed ears, '
       'amber eyes, fluffy tail behind him')

STREET = ('night time cobblestone alley, glowing street lamps, blue dark sky')

SEED_CHAR = 3300   # locks character + street
SEED_WALL = 4410   # wall / door shots
SEED_MKT  = 5520   # market shots

# (name, prompt, seed)
SHOTS = []

def fox(act, extra='', scene=STREET, seed=SEED_CHAR):
    return f"{STYLE}, full body shot, {FOX.replace('{ACT}', act)}, {extra}, {scene}"

# ── SHOT 1: establishing empty street (2 kf) ──
S1 = (f'{STYLE}, wide cinematic establishing shot of an empty {STREET}, '
      'wet cobblestones reflecting amber lamplight, deep indigo sky full of stars, '
      'no people, atmospheric fog, old european architecture')
SHOTS += [('s1_a', S1 + ', wide view', SEED_CHAR),
          ('s1_b', S1 + ', slightly closer view down the street', SEED_CHAR)]

# ── SHOT 2: Kiran walking toward camera (3 kf) ──
SHOTS += [('s2_a', fox('walking far away down the street'), SEED_CHAR),
          ('s2_b', fox('walking forward down the street'),   SEED_CHAR),
          ('s2_c', fox('walking closer toward the camera'),  SEED_CHAR)]

# ── SHOT 3: stops, looks up (2 kf) ──
SHOTS += [('s3_a', fox('standing still looking ahead'),      SEED_CHAR),
          ('s3_b', fox('standing still looking up, head tilted upward, curious'), SEED_CHAR)]

# ── SHOT 4: close up eyes (2 kf) ──
CU = (f'{STYLE}, extreme close up portrait of an orange furred fox character child face, '
      'amber eyes, fox snout, pointed ears, {EXP}, '
      'dark blue night background, warm lamplight on the fur, shallow depth of field')
SHOTS += [('s4_a', CU.replace('{EXP}','calm curious expression'), SEED_CHAR),
          ('s4_b', CU.replace('{EXP}','eyes widening in wonder, teal light reflecting in the eyes'), SEED_CHAR)]

# ── SHOT 5-6: the wall + teal door tracing (3 kf) ──
WALL = (f'{STYLE}, an old weathered stone wall in a dark night alley, '
        'ancient stone blocks, moss, {DOOR}, atmospheric, cinematic')
SHOTS += [('s5_a', WALL.replace('{DOOR}','plain empty wall, nothing unusual'), SEED_WALL),
          ('s5_b', WALL.replace('{DOOR}','a faint thin glowing teal blue line starting to trace a doorway outline on the stone'), SEED_WALL),
          ('s5_c', WALL.replace('{DOOR}','a complete glowing teal blue doorway outline carved into the stone, bright glowing edges'), SEED_WALL)]

# ── SHOT 7: door erupts (2 kf) ──
SHOTS += [('s7_a', WALL.replace('{DOOR}','a brilliant glowing teal blue magical door blazing with light, intense glow, light spilling across the alley'), SEED_WALL),
          ('s7_b', WALL.replace('{DOOR}','a blazing teal magical doorway fully open, brilliant turquoise light flooding the entire alley, warm golden light visible through the opening'), SEED_WALL)]

# ── SHOT 8: Kiran silhouetted against door (2 kf) ──
SHOTS += [('s8_a', fox('standing small facing a huge glowing teal magical door',
             'silhouetted against brilliant teal light, backlit, rim lighting',
             'dark alley, glowing teal doorway on stone wall', SEED_WALL), SEED_WALL),
          ('s8_b', fox('standing before an open glowing doorway, arms slightly raised in wonder',
             'backlit by brilliant teal and warm golden light pouring out, rim lighting',
             'dark alley, blazing open magical doorway', SEED_WALL), SEED_WALL)]

# ── SHOT 9: Chimki emerges (2 kf) ──
CHIM = (f'{STYLE}, a tiny glowing magical spirit creature floating in midair, '
        'small translucent body glowing warm golden white from within like a lantern, '
        'tiny rounded ears, large glowing eyes, wearing a tiny paper vest, '
        'sparkles and light motes around it, {POS}, '
        'dark alley with a glowing teal doorway behind, magical atmosphere')
SHOTS += [('s9_a', CHIM.replace('{POS}','emerging from a bright glowing doorway, small and distant'), SEED_WALL),
          ('s9_b', CHIM.replace('{POS}','floating close to camera, glowing brightly, detailed'), SEED_WALL)]

# ── SHOT 10: Kiran + Chimki face to face (2 kf) ──
SHOTS += [('s10_a', fox('looking at a tiny glowing golden spirit creature floating in front of his face',
              'the small glowing creature lights up his orange fur and amber eyes, warm golden glow on his face, wonder expression',
              'dark alley, teal glowing doorway behind them', SEED_WALL), SEED_WALL),
          ('s10_b', fox('smiling in wonder at a tiny glowing golden creature floating near him',
              'warm golden light on his face, amber eyes shining, teal and gold lighting, magical',
              'dark alley, brilliant teal doorway glowing behind them', SEED_WALL), SEED_WALL)]

# ── SHOT 11: market glimpse through door (2 kf) ──
MKT = (f'{STYLE}, a vast magical night bazaar market, hundreds of glowing amber paper lanterns '
       'strung overhead, deep violet starlit sky, market stalls and tents, '
       'strange magical creatures browsing and trading, warm golden light everywhere, '
       'wondrous and alive, {V}')
SHOTS += [('s11_a', MKT.replace('{V}','seen from the entrance, wide reveal'), SEED_MKT),
          ('s11_b', MKT.replace('{V}','wide sweeping view of the enormous market stretching far away'), SEED_MKT)]

print(f'Total keyframes: {len(SHOTS)}')

def fetch(item, attempt=0):
    name, prompt, seed = item
    path = os.path.join(OUT, f'{name}.jpg')
    if os.path.exists(path) and os.path.getsize(path) > 8000:
        return f'{name}: cached'
    u = (f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}'
         f'?width=1280&height=720&model=flux&nologo=true&seed={seed}&enhance=true')
    for a in range(5):
        try:
            r = requests.get(u, verify=CA, timeout=220)
            if r.status_code == 200 and len(r.content) > 8000:
                with open(path,'wb') as f: f.write(r.content)
                return f'{name}: OK {len(r.content)//1024}KB'
            if r.status_code in (429, 500, 502, 503):
                time.sleep(6 + a*7 + random.random()*4); continue
            return f'{name}: HTTP {r.status_code}'
        except Exception as e:
            time.sleep(5 + a*5)
    return f'{name}: FAILED'

# Throttled: 2 workers, stagger starts
results = []
with ThreadPoolExecutor(2) as ex:
    futs = []
    for i, item in enumerate(SHOTS):
        futs.append(ex.submit(fetch, item))
        time.sleep(2.5)
    for f in futs:
        r = f.result(); results.append(r); print(' ', r)

ok = sum(1 for r in results if 'OK' in r or 'cached' in r)
print(f'\n{ok}/{len(SHOTS)} keyframes ready')
