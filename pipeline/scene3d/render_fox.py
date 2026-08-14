#!/usr/bin/env python3
"""
Render the CC0 rigged Fox in Blender: real 3D, real skeletal animation,
camera orbiting to demonstrate true 360.
"""
import bpy, math, os, sys, mathutils, addon_utils
# Cycles renders on CPU without OpenGL; EEVEE needs libEGL which headless lacks
addon_utils.enable('cycles', default_set=True, persistent=True)

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
GLTF=os.path.join(SP,'assets3d/animals/glTF/Fox.gltf')
OUT=os.path.join(SP,'foxrender'); os.makedirs(OUT,exist_ok=True)

TEST = '--test' in sys.argv
ACTION = 'Walk'
FPS = 30
SECS = 4.0
NF = 1 if TEST else int(FPS*SECS)
RES = (960,540) if TEST else (1280,720)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLTF)

arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
fox=next(o for o in bpy.data.objects if o.type=='MESH' and o.name=='Fox')
# drop the stray helper mesh that ships with the file
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name not in ('Fox',):
        bpy.data.objects.remove(o, do_unlink=True)

# ── assign the walk action ──
act=bpy.data.actions[ACTION]
if not arm.animation_data: arm.animation_data_create()
arm.animation_data.action=act
try:                                   # Blender 4.4+ slotted actions
    if getattr(act,'slots',None):
        arm.animation_data.action_slot=act.slots[0]
except Exception: pass
a_start,a_end=[int(round(x)) for x in act.frame_range]
print(f'action {ACTION}: frames {a_start}-{a_end}')

# ── ground ──
bpy.ops.mesh.primitive_plane_add(size=60, location=(0,0,0))
ground=bpy.context.object
gm=bpy.data.materials.new('Ground'); gm.use_nodes=True
bsdf=gm.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value=(0.16,0.22,0.14,1)
bsdf.inputs['Roughness'].default_value=0.95
ground.data.materials.append(gm)

# ── lights ──
bpy.ops.object.light_add(type='SUN', location=(6,-6,10))
sun=bpy.context.object
sun.data.energy=4.0
sun.data.angle=math.radians(6)
sun.rotation_euler=(math.radians(52),0,math.radians(38))
bpy.ops.object.light_add(type='AREA', location=(-6,-4,5))
fill=bpy.context.object
fill.data.energy=180; fill.data.size=8
fill.rotation_euler=(math.radians(60),0,math.radians(-120))

# sky-ish world
world=bpy.data.worlds.new('W'); bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.42,0.58,0.78,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.6

# ── auto-frame the camera from the model's bounds ──
bpy.context.view_layer.update()
corners=[fox.matrix_world @ mathutils.Vector(v) for v in fox.bound_box]
zs=[p.z for p in corners]
height=max(zs)-min(zs)
maxdim=max(max(p.x for p in corners)-min(p.x for p in corners),
           max(p.y for p in corners)-min(p.y for p in corners),
           height)
target=bpy.data.objects.new('Target',None)
bpy.context.collection.objects.link(target)
target.location=(0,0,height*0.48)
bpy.ops.object.camera_add(location=(0,-maxdim*2.2,height*1.1))
cam=bpy.context.object
tc=cam.constraints.new('TRACK_TO'); tc.target=target
tc.track_axis='TRACK_NEGATIVE_Z'; tc.up_axis='UP_Y'
cam.data.lens=50
bpy.context.scene.camera=cam
RADIUS=maxdim*2.2
CAM_Z=height*1.1
print(f'model {maxdim:.2f} wide, {height:.2f} tall -> cam radius {RADIUS:.2f}')

# ── render settings ──
sc=bpy.context.scene
sc.render.resolution_x,sc.render.resolution_y=RES
sc.render.resolution_percentage=100
sc.render.fps=FPS
sc.render.image_settings.file_format='PNG'

try:
    sc.render.engine='CYCLES'
    sc.cycles.device='CPU'
    sc.cycles.samples=24 if not TEST else 32
    sc.cycles.use_denoising=True
    sc.cycles.max_bounces=4
except Exception as e:
    print('cycles unavailable, falling back:',e)
    sc.render.engine='BLENDER_WORKBENCH'
print('using engine:',sc.render.engine)

for i in range(NF):
    t=i/max(1,NF)
    # loop the walk action
    f=a_start+(i%(a_end-a_start+1))
    sc.frame_set(int(f))
    ang=math.radians(360.0*t)-math.pi/2
    cam.location=(math.cos(ang)*RADIUS, math.sin(ang)*RADIUS, CAM_Z)
    sc.render.filepath=os.path.join(OUT,f'{i:04d}.png')
    bpy.ops.render.render(write_still=True)
    if TEST or i%20==0: print(f'  frame {i+1}/{NF}')
print('done')
