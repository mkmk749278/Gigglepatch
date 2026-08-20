#!/usr/bin/env python3
"""
Blender scene construction for the test reel.

Cycles multithreads one frame across all cores, so rendering every frame in 3D
is ~17 h for five minutes on this box. Instead we render a small number of
high-quality PLATES here (colour + depth), and animate them in numpy where the
cost is ~0.2 s/frame across four workers.

Depth is rendered alongside colour so fog and depth-of-field can be done in the
compositor for free, instead of paying for volumetrics in Cycles.
"""
import os, sys, math, random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env

import bpy, addon_utils
from mathutils import Vector

W, H = 1920, 1080


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(samples=64, w=W, h=H):
    addon_utils.enable('cycles', default_set=True, persistent=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True          # lets us stay at low sample counts
    sc.cycles.max_bounces = 4
    sc.cycles.transmission_bounces = 2
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look = 'Medium High Contrast'
    # depth pass -> fog + DOF in the compositor
    sc.view_layers[0].use_pass_z = True
    sc.use_nodes = True
    return sc


def mat(name, base, rough=0.8, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    bsdf.inputs['Roughness'].default_value = rough
    if emit:
        bsdf.inputs['Emission Color'].default_value = (*emit, 1)
        bsdf.inputs['Emission Strength'].default_value = emit_str
    return m


def add(prim, mtl=None, **kw):
    getattr(bpy.ops.mesh, prim)(**kw)
    o = bpy.context.object
    if mtl:
        o.data.materials.append(mtl)
    return o


def tree(x, y, scale, trunk_m, leaf_m, rng):
    """Stylised low-poly conifer: a stack of shrinking cones."""
    parts = []
    t = add('primitive_cylinder_add', trunk_m, vertices=8,
            radius=0.16 * scale, depth=1.4 * scale,
            location=(x, y, 0.7 * scale))
    parts.append(t)
    n = rng.randint(3, 4)
    for i in range(n):
        f = 1.0 - i * 0.22
        c = add('primitive_cone_add', leaf_m, vertices=9,
                radius1=0.95 * scale * f, depth=1.5 * scale * f,
                location=(x, y, (1.25 + i * 0.72) * scale))
        c.rotation_euler[2] = rng.uniform(0, 3.14)
        parts.append(c)
    return parts


def lantern(x, y, z, glass_m, rng):
    o = add('primitive_uv_sphere_add', glass_m, segments=12, ring_count=8,
            radius=0.22, location=(x, y, z))
    o.scale = (1, 1, 1.25)
    lt = bpy.data.lights.new('lamp', 'POINT')
    lt.energy = rng.uniform(120, 190)
    lt.color = (1.0, 0.72, 0.36)
    lt.shadow_soft_size = 0.5
    ob = bpy.data.objects.new('lamp', lt)
    ob.location = (x, y, z)
    bpy.context.collection.objects.link(ob)
    return o


def world_night(top=(0.012, 0.020, 0.058), horizon=(0.050, 0.045, 0.100), strength=1.35):
    w = bpy.data.worlds.new('night')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    grad = nt.nodes.new('ShaderNodeTexGradient')
    grad.gradient_type = 'EASING'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    tex = nt.nodes.new('ShaderNodeTexCoord')
    map_ = nt.nodes.new('ShaderNodeMapping')
    map_.inputs['Rotation'].default_value = (1.5708, 0, 0)
    nt.links.new(tex.outputs['Generated'], map_.inputs['Vector'])
    nt.links.new(map_.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    return w


def camera(loc, look_at, lens=40):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = lens
    d = Vector(look_at) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    return cam


def path_ribbon(fn, t0=0.0, t1=1.0, steps=120, width=1.9, z=0.03, mtl=None,
                name='path'):
    """
    A path as a single quad strip.

    Built from overlapping discs it shadow-acnes badly: every disc shadows its
    neighbour and the whole band crushes to black. One continuous mesh has no
    coplanar neighbours to self-shadow.

    `fn(t)` returns the centreline (x, y) for t in [0, 1].
    """
    verts, faces = [], []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        x, y = fn(t)
        nx, ny = fn(min(1.0, t + 1e-3))
        dx, dy = nx - x, ny - y
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L          # left normal
        verts.append((x + px * width, y + py * width, z))
        verts.append((x - px * width, y - py * width, z))
    for i in range(steps):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if mtl:
        ob.data.materials.append(mtl)
    return ob
