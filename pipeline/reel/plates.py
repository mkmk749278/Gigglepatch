#!/usr/bin/env python3
"""Build the midnight-forest set and render colour + depth plates."""
import os, sys, math, random, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, scene as S
import bpy


def build_forest(seed=7):
    rng = random.Random(seed)
    S.reset()
    sc = S.setup_render(samples=int(os.environ.get('REEL_SAMPLES', 64)),
                        w=int(os.environ.get('REEL_W', 1920)),
                        h=int(os.environ.get('REEL_H', 1080)))
    S.world_night()

    trunk = S.mat('trunk', (0.14, 0.09, 0.07), rough=0.95)
    leaf_a = S.mat('leafA', (0.030, 0.105, 0.080), rough=0.9)
    leaf_b = S.mat('leafB', (0.038, 0.082, 0.120), rough=0.9)
    ground = S.mat('ground', (0.085, 0.095, 0.125), rough=1.0)
    glass = S.mat('glass', (1.0, 0.60, 0.26), rough=0.3,
                  emit=(1.0, 0.58, 0.22), emit_str=6.0)
    path_m = S.mat('path', (0.26, 0.21, 0.16), rough=1.0)

    g = S.add('primitive_plane_add', ground, size=140)
    g.location = (0, 0, 0)

    # winding path the camera follows -- one ribbon mesh, see scene.path_ribbon
    def centre(t):
        return (math.sin(t * 5.2) * 3.4, -18 + t * 74)
    S.path_ribbon(centre, steps=160, width=2.0, z=0.03, mtl=path_m)

    # trees flanking the path, denser far away for depth
    for i in range(150):
        side = 1 if i % 2 else -1
        t = rng.random()
        y = -18 + t * 74
        x = centre(t)[0] + side * rng.uniform(4.4, 18.0)
        sc_ = rng.uniform(1.5, 3.4)
        S.tree(x, y, sc_, trunk, leaf_a if rng.random() < .6 else leaf_b, rng)

    # lanterns strung along the path — the only warm light in frame
    for i in range(26):
        t = i / 26.0
        y = -14 + t * 76
        x = math.sin(t * 5.2) * 3.4 + (1.9 if i % 2 else -1.9)
        S.lantern(x, y, rng.uniform(2.6, 3.9), glass, rng)

    # cool moon key from behind, separates trees from sky
    moon = bpy.data.lights.new('moon', 'SUN')
    moon.energy = 0.9
    moon.color = (0.42, 0.56, 1.0)
    moon.angle = 0.12
    mo = bpy.data.objects.new('moon', moon)
    mo.rotation_euler = (0.55, 0.2, 2.5)
    bpy.context.collection.objects.link(mo)
    return sc


def wire_depth_output(sc, outdir, tag):
    """Colour to Composite, normalised depth to a 16-bit PNG next to it."""
    nt = sc.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers')
    comp = nt.nodes.new('CompositorNodeComposite')
    nt.links.new(rl.outputs['Image'], comp.inputs['Image'])

    mr = nt.nodes.new('CompositorNodeMapRange')
    mr.inputs['From Min'].default_value = 4.0
    mr.inputs['From Max'].default_value = 70.0
    mr.inputs['To Min'].default_value = 0.0
    mr.inputs['To Max'].default_value = 1.0
    mr.use_clamp = True
    nt.links.new(rl.outputs['Depth'], mr.inputs['Value'])

    fo = nt.nodes.new('CompositorNodeOutputFile')
    fo.base_path = outdir
    fo.format.file_format = 'PNG'
    fo.format.color_mode = 'BW'
    fo.format.color_depth = '16'
    fo.file_slots[0].path = f'{tag}_depth_'
    nt.links.new(mr.outputs['Value'], fo.inputs[0])


def render_plate(sc, tag, cam_loc, look_at, lens=40):
    outdir = os.path.join(env.SP, 'plates')
    os.makedirs(outdir, exist_ok=True)
    S.camera(cam_loc, look_at, lens)
    wire_depth_output(sc, outdir, tag)
    sc.render.filepath = os.path.join(outdir, f'{tag}.png')
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


if __name__ == '__main__':
    sc = build_forest()
    dt = render_plate(sc, 'probe', (0.5, -16, 2.4), (0.5, 6, 2.0))
    print(f'\nPLATE_SECONDS {dt:.1f}')
