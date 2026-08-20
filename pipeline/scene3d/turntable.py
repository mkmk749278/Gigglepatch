#!/usr/bin/env python3
"""Software turntable renderer — proves the mesh is real 3D (any angle)."""
import numpy as np, trimesh, math, os, sys
from PIL import Image, ImageDraw
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != '/' and not _os.path.exists(_os.path.join(_d, 'env.py')):
    _d = _os.path.dirname(_d)
_sys.path.insert(0, _d)
from env import SP
MESH=os.path.join(SP,'triposr/out3d/0/mesh.glb')
OUT=os.path.join(SP,'turntable'); os.makedirs(OUT,exist_ok=True)
S=560
LIGHT=np.array([0.35,0.55,0.75]); LIGHT=LIGHT/np.linalg.norm(LIGHT)

m=trimesh.load(MESH,force='mesh')
V=np.asarray(m.vertices,dtype=np.float64)
Fc=np.asarray(m.faces,dtype=np.int64)
try:
    VC=np.asarray(m.visual.vertex_colors,dtype=np.float64)[:,:3]/255.0
except Exception:
    VC=np.ones((len(V),3))*0.75
# TripoSR emits the figure lying along +X — stand it up (X becomes up)
V=V[:,[2,0,1]]
V[:,1]*=-1
# centre + normalise scale
V=V-V.mean(axis=0)
V=V/np.abs(V).max()

def render(yaw_deg, pitch_deg=8.0):
    cy,sy=math.cos(math.radians(yaw_deg)),math.sin(math.radians(yaw_deg))
    cp,sp=math.cos(math.radians(pitch_deg)),math.sin(math.radians(pitch_deg))
    Ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rx=np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])
    P=V@Ry.T@Rx.T

    # face depth + normal
    a,b,c=P[Fc[:,0]],P[Fc[:,1]],P[Fc[:,2]]
    N=np.cross(b-a,c-a)
    ln=np.linalg.norm(N,axis=1,keepdims=True); ln[ln==0]=1; N=N/ln
    depth=(a[:,2]+b[:,2]+c[:,2])/3.0
    vis=N[:,2]>-0.05                       # cull hard back-faces
    idx=np.argsort(depth)                  # painter's: far -> near
    idx=idx[vis[idx]]

    shade=np.clip(N@LIGHT,0,1)*0.75+0.25
    fcol=(VC[Fc[:,0]]+VC[Fc[:,1]]+VC[Fc[:,2]])/3.0
    col=np.clip(fcol*shade[:,None],0,1)

    # to screen
    sx=(P[:,0]*0.46+0.5)*S
    sy_=(0.5-P[:,1]*0.46)*S
    img=Image.new('RGB',(S,S),(238,238,243))
    d=ImageDraw.Draw(img)
    for i in idx:
        f=Fc[i]
        d.polygon([(sx[f[0]],sy_[f[0]]),(sx[f[1]],sy_[f[1]]),(sx[f[2]],sy_[f[2]])],
                  fill=tuple((col[i]*255).astype(np.uint8)))
    return img

if __name__=='__main__':
    n=int(sys.argv[1]) if len(sys.argv)>1 else 8
    for i in range(n):
        yaw=360.0*i/n
        render(yaw).save(os.path.join(OUT,f'{i:03d}.png'))
        print(f'  {i+1}/{n}  yaw={yaw:.0f}')
