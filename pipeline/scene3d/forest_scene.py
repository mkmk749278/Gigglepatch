#!/usr/bin/env python3
"""
Forest test shot — CC0 rigged fox walking through a CC0 forest.
Ground speed is matched to the measured stride so the paws don't skate.
"""
import bpy, math, os, sys, random, mathutils, addon_utils
addon_utils.enable('cycles', default_set=True, persistent=True)
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != '/' and not _os.path.exists(_os.path.join(_d, 'env.py')):
    _d = _os.path.dirname(_d)
_sys.path.insert(0, _d)
from env import SP
A=os.path.join(SP,'assets3d')
OUT=os.path.join(SP,'forest'); os.makedirs(OUT,exist_ok=True)

TEST='--test' in sys.argv
FPS=24
RES=(960,540)

# measured from the Walk action: foot planted frames 0-12, travels 1.03 units
STANCE_FRAMES=12.0
STANCE_TRAVEL=1.03
UNITS_PER_FRAME=STANCE_TRAVEL/STANCE_FRAMES     # 0.0858
FOX_FWD=mathutils.Vector((0,-1,0))               # fox faces -Y

# shot list: (name, seconds)
SHOTS=[('wide',5.0),('track',5.0),('front',4.0),('close',4.0)]
if TEST: SHOTS=[('wide',None)]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.fps=FPS
sc.render.resolution_x,sc.render.resolution_y=RES
sc.render.image_settings.file_format='PNG'
sc.render.engine='CYCLES'
sc.cycles.device='CPU'
sc.cycles.samples=20
sc.cycles.use_denoising=True
sc.cycles.max_bounces=3

# ── fox ──
bpy.ops.import_scene.gltf(filepath=os.path.join(A,'animals/glTF/Fox.gltf'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name!='Fox':
        bpy.data.objects.remove(o,do_unlink=True)
act=bpy.data.actions['Walk']
arm.animation_data_create(); arm.animation_data.action=act
try:
    if getattr(act,'slots',None): arm.animation_data.action_slot=act.slots[0]
except Exception: pass
A0,A1=[int(round(x)) for x in act.frame_range]
CYCLE=A1-A0
fox_root=arm            # move the armature; the mesh is parented to it

# ── ground ──
bpy.ops.mesh.primitive_plane_add(size=400)
gnd=bpy.context.object
m=bpy.data.materials.new('Grass'); m.use_nodes=True
b=m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value=(0.13,0.26,0.11,1)
b.inputs['Roughness'].default_value=0.95
gnd.data.materials.append(m)

# ── scatter the forest ──
rng=random.Random(7)
FBX=os.path.join(A,'nature/FBX')
def pick(prefix,n):
    fs=[f for f in os.listdir(FBX) if f.startswith(prefix) and f.endswith('.fbx')
        and 'Snow' not in f and 'Dead' not in f]
    return rng.sample(fs,min(n,len(fs)))

cache={}
def load_fbx(fn):
    if fn in cache: return cache[fn]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX,fn))
    new=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
    if not new: return None
    src=new[0]
    for o in set(bpy.data.objects)-before:
        if o is not src: bpy.data.objects.remove(o,do_unlink=True)
    src.hide_render=True; src.hide_viewport=True
    cache[fn]=src
    return src

# The fox rig is ~20x larger than the nature assets, so normalise everything
# to real-world heights. Fox is 2.62 units tall ~= a 0.45 m fox.
UNITS_PER_M=2.62/0.45          # ~5.8 units per metre

def scatter(prefix,count,rmin,rmax,target_m,jitter,avoid=3.5):
    files=pick(prefix,6)
    if not files: return
    placed=0; tries=0
    while placed<count and tries<count*12:
        tries+=1
        ang=rng.uniform(0,2*math.pi); rad=rng.uniform(rmin,rmax)
        x=math.cos(ang)*rad; y=math.sin(ang)*rad
        if abs(x)<avoid and -70<y<30:      # keep the fox's path clear
            continue
        src=load_fbx(rng.choice(files))
        if src is None: continue
        o=src.copy(); o.data=src.data
        bpy.context.collection.objects.link(o)
        o.hide_render=False; o.hide_viewport=False
        o.scale=(1,1,1); bpy.context.view_layer.update()
        h=max(o.dimensions.z,1e-4)
        want=rng.uniform(*jitter)*target_m*UNITS_PER_M
        s=want/h
        o.scale=(s,s,s)
        o.location=(x,y,0)
        o.rotation_euler=(0,0,rng.uniform(0,2*math.pi))
        placed+=1

#        prefix        n   rmin rmax  height(m)  jitter
scatter('CommonTree', 46,  10,  95,   7.5, (0.75,1.3))
scatter('BirchTree',  30,  12,  95,   8.5, (0.75,1.3))
scatter('PineTree',   22,  14,  95,   9.5, (0.8,1.3))
scatter('Bush',       40,   6,  60,   1.1, (0.7,1.4), avoid=3.0)
scatter('Rock',       24,   6,  60,   0.7, (0.6,1.6), avoid=3.0)
scatter('Grass',      70,   4,  45,   0.35,(0.7,1.5), avoid=1.8)
scatter('Flowers',    30,   4,  40,   0.3, (0.7,1.4), avoid=1.8)
scatter('TreeStump',  10,  10,  55,   0.6, (0.8,1.2))
print('scene objects:',len(bpy.data.objects))

# ── material palette: the FBX colours import almost black, so restate them ──
PALETTE={
 'Wood':      (0.24,0.13,0.07),
 'DarkWood':  (0.17,0.09,0.05),
 'Green':     (0.16,0.40,0.11),
 'DarkGreen': (0.09,0.26,0.08),
 'LightGreen':(0.26,0.52,0.16),
 'Stone':     (0.34,0.34,0.36),
 'Rock':      (0.32,0.32,0.34),
 'Grey':      (0.33,0.33,0.35),
 'Red':       (0.45,0.09,0.08),
 'Yellow':    (0.72,0.55,0.10),
 'White':     (0.80,0.80,0.78),
 'Pink':      (0.66,0.32,0.42),
 'Purple':    (0.36,0.20,0.48),
 'Blue':      (0.14,0.26,0.50),
 'Brown':     (0.26,0.16,0.09),
}
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not bs: continue
    key=next((k for k in PALETTE if k.lower()==mat.name.split('.')[0].lower()),None)
    if key:
        c=PALETTE[key]
    else:
        # unknown name: lift the too-dark imported colour
        o=bs.inputs['Base Color'].default_value
        c=tuple(min(1.0,v*3.2) for v in o[:3])
    bs.inputs['Base Color'].default_value=(*c,1.0)
    bs.inputs['Roughness'].default_value=0.9
print('materials restated:',len(bpy.data.materials))

# ── light: warm late-afternoon sun ──
bpy.ops.object.light_add(type='SUN',location=(20,-30,40))
sun=bpy.context.object
sun.data.energy=3.6; sun.data.angle=math.radians(3)
sun.data.color=(1.0,0.93,0.80)
sun.rotation_euler=(math.radians(48),0,math.radians(28))
w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
bg=w.node_tree.nodes['Background']
bg.inputs['Color'].default_value=(0.45,0.62,0.85,1)
bg.inputs['Strength'].default_value=0.75

# ── camera ──
tgt=bpy.data.objects.new('Tgt',None); bpy.context.collection.objects.link(tgt)
bpy.ops.object.camera_add(location=(0,0,3))
cam=bpy.context.object
tc=cam.constraints.new('TRACK_TO'); tc.target=tgt
tc.track_axis='TRACK_NEGATIVE_Z'; tc.up_axis='UP_Y'
sc.camera=cam

def fox_at(fi):
    """Place the fox for global frame index fi; returns its location."""
    y=18.0-UNITS_PER_FRAME*fi        # walks toward -Y
    fox_root.location=(0,y,0)
    fox_root.rotation_euler=(0,0,0)
    sc.frame_set(A0+(fi%CYCLE))
    return mathutils.Vector((0,y,0))

frame=0
for (name,secs) in SHOTS:
    n=1 if TEST else int(secs*FPS)
    for k in range(n):
        loc=fox_at(frame)
        cx=loc.x; cy=loc.y;
        if name=='wide':
            tgt.location=(cx,cy,1.0)
            cam.location=(cx+9,cy-11,4.2); cam.data.lens=42
        elif name=='track':
            tgt.location=(cx,cy,1.1)
            cam.location=(cx+7.5,cy-1.0,1.9); cam.data.lens=55
        elif name=='front':
            tgt.location=(cx,cy,1.1)
            cam.location=(cx+1.2,cy-8.5,1.6); cam.data.lens=60
        else:  # close
            tgt.location=(cx,cy+0.3,1.5)
            cam.location=(cx+3.2,cy-3.4,1.5); cam.data.lens=80
        sc.render.filepath=os.path.join(OUT,f'{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        frame+=1
        if TEST or frame%24==0: print(f'  {name} frame {frame}')
print('done')
