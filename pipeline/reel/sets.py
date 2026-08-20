#!/usr/bin/env python3
"""
The three environments the reel is shot in.

Building a set is cheap; rendering is not. Each builder is therefore called
once and then shot from several cameras, so a 12-shot reel costs 12 renders
rather than 12 rebuilds.
"""
import os, sys, math, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, scene as S
import bpy


def _common(samples=None, w=None, h=None):
    S.reset()
    return S.setup_render(
        samples=int(samples or os.environ.get('REEL_SAMPLES', 48)),
        w=int(w or os.environ.get('REEL_W', 1280)),
        h=int(h or os.environ.get('REEL_H', 720)))


def _palette():
    return dict(
        trunk=S.mat('trunk', (0.14, 0.09, 0.07), rough=0.95),
        leaf_a=S.mat('leafA', (0.030, 0.105, 0.080), rough=0.9),
        leaf_b=S.mat('leafB', (0.038, 0.082, 0.120), rough=0.9),
        ground=S.mat('ground', (0.085, 0.095, 0.125), rough=1.0),
        path=S.mat('path', (0.26, 0.21, 0.16), rough=1.0),
        glass=S.mat('glass', (1.0, 0.60, 0.26), rough=0.3,
                    emit=(1.0, 0.58, 0.22), emit_str=6.0),
        cloth_a=S.mat('clothA', (0.34, 0.10, 0.16), rough=0.85),
        cloth_b=S.mat('clothB', (0.10, 0.16, 0.30), rough=0.85),
        cloth_c=S.mat('clothC', (0.30, 0.20, 0.06), rough=0.85),
        wood=S.mat('wood', (0.17, 0.11, 0.07), rough=0.9),
        teal=S.mat('teal', (0.10, 0.62, 0.60), rough=0.25,
                   emit=(0.10, 0.75, 0.72), emit_str=5.0),
    )


def _moon(energy=0.9, rot=(0.55, 0.2, 2.5)):
    lt = bpy.data.lights.new('moon', 'SUN')
    lt.energy, lt.color, lt.angle = energy, (0.42, 0.56, 1.0), 0.12
    o = bpy.data.objects.new('moon', lt)
    o.rotation_euler = rot
    bpy.context.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- forest

def forest(seed=7):
    rng = random.Random(seed)
    sc = _common()
    S.world_night()
    P = _palette()

    g = S.add('primitive_plane_add', P['ground'], size=140)

    def centre(t):
        return (math.sin(t * 5.2) * 3.4, -18 + t * 74)
    S.path_ribbon(centre, steps=160, width=2.0, z=0.03, mtl=P['path'])

    for i in range(150):
        side = 1 if i % 2 else -1
        t = rng.random()
        x = centre(t)[0] + side * rng.uniform(4.4, 18.0)
        S.tree(x, -18 + t * 74, rng.uniform(1.5, 3.4), P['trunk'],
               P['leaf_a'] if rng.random() < .6 else P['leaf_b'], rng)

    for i in range(26):
        t = i / 26.0
        x = centre(t)[0] + (1.9 if i % 2 else -1.9)
        S.lantern(x, -14 + t * 76, rng.uniform(2.6, 3.9), P['glass'], rng)

    _moon()
    return sc


# ---------------------------------------------------------------- market

def market(seed=11):
    """Stalls either side of a wide lane -- the reel's busiest frame."""
    rng = random.Random(seed)
    sc = _common()
    S.world_night(top=(0.020, 0.016, 0.055), horizon=(0.085, 0.050, 0.095))
    P = _palette()

    S.add('primitive_plane_add', P['ground'], size=160)
    S.path_ribbon(lambda t: (0.0, -20 + t * 78), steps=60, width=4.6,
                  z=0.03, mtl=P['path'])

    cloths = [P['cloth_a'], P['cloth_b'], P['cloth_c']]
    for i in range(22):
        t = i / 22.0
        side = 1 if i % 2 else -1
        y = -16 + t * 72
        x = side * rng.uniform(5.4, 7.0)
        depth = rng.uniform(0.9, 1.5)

        # counter
        c = S.add('primitive_cube_add', P['wood'], size=1,
                  location=(x, y, 0.62))
        c.scale = (1.5, depth * 1.6, 0.62)
        # posts + awning
        for dx_ in (-1.35, 1.35):
            for dy_ in (-depth * 1.4, depth * 1.4):
                p = S.add('primitive_cylinder_add', P['wood'], vertices=6,
                          radius=0.07, depth=2.6,
                          location=(x + dx_, y + dy_, 1.3))
        aw = S.add('primitive_cube_add', cloths[i % 3], size=1,
                   location=(x, y, 2.62))
        aw.scale = (1.75, depth * 1.75, 0.05)
        aw.rotation_euler = (math.radians(-9 * side), 0, 0)
        # wares
        for _ in range(rng.randint(2, 4)):
            b = S.add('primitive_cube_add', cloths[rng.randrange(3)], size=1,
                      location=(x + rng.uniform(-1.1, 1.1),
                                y + rng.uniform(-1.0, 1.0), 1.36))
            b.scale = (0.17, 0.17, 0.14)
            b.rotation_euler = (0, 0, rng.uniform(0, 3.14))

        S.lantern(x - side * 1.5, y, 2.35, P['glass'], rng)

    # a few trees behind the stalls to close the lane off
    for i in range(40):
        side = 1 if i % 2 else -1
        S.tree(side * rng.uniform(10, 22), rng.uniform(-20, 58),
               rng.uniform(2.0, 3.6), P['trunk'], P['leaf_b'], rng)

    _moon(energy=0.55)
    return sc


# ---------------------------------------------------------------- door

def door(seed=3):
    """A clearing with a standing teal portal -- the reel's hero image."""
    rng = random.Random(seed)
    sc = _common()
    S.world_night(top=(0.010, 0.018, 0.050), horizon=(0.040, 0.055, 0.105))
    P = _palette()

    S.add('primitive_plane_add', P['ground'], size=140)
    S.path_ribbon(lambda t: (0.0, -22 + t * 40), steps=50, width=2.1,
                  z=0.03, mtl=P['path'])

    # ring of trees around the clearing
    for i in range(90):
        a = rng.uniform(0, 6.283)
        r = rng.uniform(11, 24)
        S.tree(math.cos(a) * r, 8 + math.sin(a) * r, rng.uniform(1.8, 3.6),
               P['trunk'], P['leaf_a'] if rng.random() < .5 else P['leaf_b'], rng)

    # the door: a glowing slab in a rough stone frame
    slab = S.add('primitive_cube_add', P['teal'], size=1, location=(0, 8, 2.3))
    slab.scale = (1.15, 0.06, 2.25)
    for dx_ in (-1.32, 1.32):
        c = S.add('primitive_cube_add', P['wood'], size=1,
                  location=(dx_, 8, 2.35))
        c.scale = (0.17, 0.22, 2.45)
    lintel = S.add('primitive_cube_add', P['wood'], size=1, location=(0, 8, 4.9))
    lintel.scale = (1.55, 0.24, 0.2)

    key = bpy.data.lights.new('doorlight', 'AREA')
    key.energy, key.color, key.size = 420, (0.30, 0.95, 0.90), 3.0
    ko = bpy.data.objects.new('doorlight', key)
    ko.location = (0, 6.4, 2.4)
    ko.rotation_euler = (1.5708, 0, 0)
    bpy.context.collection.objects.link(ko)

    for i in range(10):
        a = i / 10.0 * 6.283
        S.lantern(math.cos(a) * 7.5, 8 + math.sin(a) * 7.5,
                  rng.uniform(2.4, 3.6), P['glass'], rng)

    _moon(energy=0.7)
    return sc


SETS = {'forest': forest, 'market': market, 'door': door}
