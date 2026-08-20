#!/usr/bin/env python3
"""Regenerate the keyframes that came back wrong."""
import requests, urllib.parse, os, time, random
from concurrent.futures import ThreadPoolExecutor

CA='/root/.ccr/ca-bundle.crt'
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != '/' and not _os.path.exists(_os.path.join(_d, 'env.py')):
    _d = _os.path.dirname(_d)
_sys.path.insert(0, _d)
from env import KF as OUT
STYLE=('Pixar DreamWorks 3D animation style, cinematic lighting, depth of field, '
       'high detail, volumetric light, 3D animated movie screenshot')
FOX=('a fox character child {ACT}, dressed in a navy pocket jacket and brown boots, '
     'standing upright on two legs, orange furred fox head with snout and pointed ears, '
     'amber eyes, fluffy tail behind him')
# historic street, explicitly no modern elements
STREET=('narrow historic medieval cobblestone alley at night, old stone buildings, '
        'glowing warm gas street lamps, deep blue night sky, '
        'no cars, no modern vehicles, no signs, no people')

SC=3300; SW=4410; SM=5520

def fox(act, extra=''):
    return f"{STYLE}, full body shot, {FOX.replace('{ACT}',act)}, {extra}, {STREET}"

# Magic door = FLAT WALL + rectangle of light. Never the word 'doorway'/'arch'.
def wall(desc):
    return (f'{STYLE}, a flat solid vertical old stone wall filling the frame, '
            f'weathered stone blocks, flat wall surface, narrow dark alley at night, '
            f'{desc}, cinematic, atmospheric, no arch, no tunnel, no opening in the wall')

FIX={
 # cars removed
 's2_a': fox('walking far away down the street'),
 's2_b': fox('walking forward down the street'),
 's2_c': fox('walking closer toward the camera'),
 # door = light on a flat wall
 's5_b': wall('a very faint thin line of glowing teal blue light beginning to draw a tall '
              'rectangle shape on the flat stone surface, subtle, barely visible'),
 's5_c': wall('a complete tall rectangle outline drawn in bright glowing teal blue light '
              'on the flat stone surface, the glowing outline sits on top of the solid wall, '
              'bright turquoise light lines, magical runes glowing along the outline'),
 's7_a': wall('a tall rectangle of blazing bright teal blue light burning on the flat stone '
              'surface, intense turquoise glow spilling outward across the stones, '
              'brilliant magical light, lens flare'),
 's7_b': wall('a tall rectangle on the wall blazing with blinding brilliant teal white light, '
              'warm golden light beginning to shine through from within the glowing rectangle, '
              'intense magical radiance flooding the alley, god rays, lens flare'),
 # keep the alley environment; avoid 'silhouette/backlit' (triggers studio bg)
 's8_a': fox('standing in the alley looking up at a huge glowing teal rectangle of light on the stone wall',
             'bright teal light from the wall illuminating his orange fur and navy jacket, '
             'his back partly to camera, small against the enormous glowing wall'),
 's8_b': fox('standing in the alley with arms slightly raised in wonder before a blazing teal light on the wall',
             'brilliant teal and warm golden light washing over him, dramatic rim light on his fur, '
             'small figure against the huge glowing wall'),
 's10_a': fox('in the alley looking at a tiny glowing golden spirit floating in front of him',
              'the tiny floating light illuminates his face, warm golden glow on orange fur, '
              'teal glow from the wall behind, wonder expression'),
 's10_b': fox('in the alley smiling with wonder at a small glowing golden spirit floating near his face',
              'warm gold light on his face and amber eyes, teal light from the wall behind him, '
              'magical two tone lighting'),
 # brighter, richer market
 's11_a': (f'{STYLE}, a vast magical night bazaar, hundreds of glowing amber and gold paper lanterns '
           'strung overhead in dense clusters, deep violet starlit sky, colourful market stalls and tents, '
           'many strange friendly magical creatures browsing and trading, '
           'rich warm golden light everywhere, glowing wares on the stalls, '
           'wondrous alive and bustling, seen from the entrance'),
 's11_b': (f'{STYLE}, enormous magical night bazaar stretching into the distance, '
           'thousands of warm glowing lanterns overhead, violet starry sky with two moons, '
           'endless colourful stalls, crowds of magical creatures, glowing magical goods, '
           'rich amber and gold light, spectacular wide establishing reveal, epic scale'),
}
SEEDS={'s2_a':SC,'s2_b':SC,'s2_c':SC,'s5_b':SW,'s5_c':SW,'s7_a':SW,'s7_b':SW,
       's8_a':SW,'s8_b':SW,'s10_a':SW,'s10_b':SW,'s11_a':SM,'s11_b':SM}

def fetch(kv):
    name,prompt=kv
    seed=SEEDS[name]
    u=(f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}'
       f'?width=1280&height=720&model=flux&nologo=true&seed={seed}&enhance=true')
    for a in range(5):
        try:
            r=requests.get(u,verify=CA,timeout=220)
            if r.status_code==200 and len(r.content)>8000:
                open(os.path.join(OUT,f'{name}.jpg'),'wb').write(r.content)
                return f'{name}: OK {len(r.content)//1024}KB'
            if r.status_code in (429,500,502,503):
                time.sleep(6+a*7+random.random()*4); continue
            return f'{name}: HTTP {r.status_code}'
        except Exception as e:
            time.sleep(5+a*5)
    return f'{name}: FAILED'

with ThreadPoolExecutor(2) as ex:
    futs=[]
    for item in FIX.items():
        futs.append(ex.submit(fetch,item)); time.sleep(2.5)
    for f in futs: print(' ',f.result())
print('done')
