#!/usr/bin/env python3
"""
Kiran cutout rig — build once, pose forever.
Same principle as a game character: one asset, transformed per frame.
"""
import numpy as np, math, os
from PIL import Image, ImageDraw, ImageFilter
import cv2

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
SRC=os.path.join(SP,'kiran_cut.png')

BASE=Image.open(SRC).convert('RGBA')
BW,BH=BASE.size          # 597 x 844

# ── PART REGIONS (x0,y0,x1,y1) and PIVOTS in base coords ────────────────────
PARTS={
 'head'  : dict(box=(50,   0,  550, 230), pivot=(300, 214)),
 'arm_l' : dict(box=(0,   270, 150, 610), pivot=(100, 300)),
 'arm_r' : dict(box=(450, 270, 597, 610), pivot=(497, 300)),
 'leg_l' : dict(box=(105, 540, 300, 844), pivot=(232, 556)),
 'leg_r' : dict(box=(298, 540, 490, 844), pivot=(352, 556)),
}
# face feature coords (base coords, read off the reference grid)
EYE_L=(220,133); EYE_R=(377,133); EYE_RX,EYE_RY=25,14
MOUTH=(300,183); MOUTH_RX=30
FUR      =(203,124,56)     # fur above the eyes
FUR_DARK =(150,84,34)
MOUTH_IN =(54,26,24)
TONGUE   =(172,82,92)

def _soft_mask(size, box, feather=9):
    m=Image.new('L',size,0)
    ImageDraw.Draw(m).rectangle(box,fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))

def build_parts():
    """
    Split the base into limb layers. The torso keeps the FULL base image —
    limbs are drawn on top of it, so no inpainting and no holes.
    """
    parts={}
    for name,cfg in PARTS.items():
        m=_soft_mask(BASE.size,cfg['box'])
        layer=Image.new('RGBA',BASE.size,(0,0,0,0))
        layer.paste(BASE,(0,0),m)
        parts[name]=dict(img=layer,pivot=cfg['pivot'])
    # torso keeps the full base, except the upper head — the head layer always
    # covers that area, so erasing it stops the ears ghosting when the head turns
    torso=BASE.copy()
    ta=np.array(torso)
    fade=np.ones((BH,BW),np.float32)
    fade[:196,:]=0.0
    for i,y in enumerate(range(196,214)):        # soft seam at the neck
        fade[y,:]=i/18.0
    ta[:,:,3]=(ta[:,:,3].astype(np.float32)*fade).astype(np.uint8)
    parts['torso']=dict(img=Image.fromarray(ta,'RGBA'),pivot=(300,420))
    return parts

PARTS_IMG=build_parts()

def _rot_about(layer, pivot, ang, offset=(0,0)):
    """Rotate an RGBA layer about a pivot, keeping canvas size; then translate."""
    if abs(ang)<0.01 and offset==(0,0): return layer
    px,py=pivot
    out=layer.rotate(ang,resample=Image.BICUBIC,center=(px,py))
    if offset!=(0,0):
        out=out.transform(out.size,Image.AFFINE,(1,0,-offset[0],0,1,-offset[1]),
                          resample=Image.BICUBIC)
    return out

def draw_face(canvas, pose):
    """Blink + mouth overlays, drawn in base coords (head-local)."""
    blink=pose.get('blink',0.0)          # 0 open .. 1 closed
    mouth=pose.get('mouth',0.0)          # 0 closed .. 1 open

    if blink>0.04:
        # eyelid = real brow fur slid down over the eye, clipped to the eye shape
        lid=Image.new('RGBA',canvas.size,(0,0,0,0))
        for (ex,ey) in (EYE_L,EYE_R):
            drop=(2*EYE_RY+6)*blink
            # brow fur sampled from just above the eye
            bx0,bx1=ex-EYE_RX-6,ex+EYE_RX+6
            by0,by1=int(ey-EYE_RY*2-16),int(ey-EYE_RY-1)
            brow=BASE.crop((bx0,max(0,by0),bx1,max(1,by1)))
            brow=brow.resize((bx1-bx0,max(1,int((by1-by0)*1.35))),Image.BICUBIC)
            tmp=Image.new('RGBA',canvas.size,(0,0,0,0))
            tmp.paste(brow,(bx0,int(by0+drop)))
            # clip to eye ellipse ∩ curtain
            eye=Image.new('L',canvas.size,0)
            ImageDraw.Draw(eye).ellipse(
                [ex-EYE_RX-2,ey-EYE_RY-2,ex+EYE_RX+2,ey+EYE_RY+2],fill=255)
            cur=Image.new('L',canvas.size,0)
            close_y=ey-EYE_RY-2+drop
            ImageDraw.Draw(cur).rectangle(
                [ex-EYE_RX-6,ey-EYE_RY-10,ex+EYE_RX+6,close_y],fill=255)
            m=Image.fromarray(np.minimum(np.array(eye),np.array(cur))
                              ).filter(ImageFilter.GaussianBlur(1.0))
            lid.paste(tmp,(0,0),m)
            if blink>0.6:
                ImageDraw.Draw(lid).arc(
                    [ex-EYE_RX,close_y-7,ex+EYE_RX,close_y+4],205,335,
                    fill=(*FUR_DARK,200),width=2)
        canvas.alpha_composite(lid)

    if mouth>0.05:
        mx,my=MOUTH
        h=3.0+11.0*mouth                 # jaw drop
        w=MOUTH_RX*(0.80+0.20*mouth)     # widens only slightly
        mo=Image.new('RGBA',canvas.size,(0,0,0,0))
        dm=ImageDraw.Draw(mo)
        dm.ellipse([mx-w,my-h*0.25,mx+w,my+h],fill=(42,20,20,248))
        if mouth>0.62:                   # a hint of tongue only when wide open
            t=(mouth-0.62)/0.38
            dm.ellipse([mx-w*0.42,my+h*0.42,mx+w*0.42,my+h*0.86],
                       fill=(150,74,80,int(190*t)))
        canvas.alpha_composite(mo.filter(ImageFilter.GaussianBlur(1.6)))

def render_pose(pose, scale=1.0, canvas_pad=180):
    """
    pose keys: body_y, body_rot, head_rot, head_y, arm_l, arm_r,
               leg_l, leg_r, blink, mouth
    Returns RGBA image of the posed character.
    """
    W2,H2=BW+canvas_pad*2, BH+canvas_pad*2
    canvas=Image.new('RGBA',(W2,H2),(0,0,0,0))
    off=(canvas_pad,canvas_pad)

    def place(layer):
        canvas.alpha_composite(layer,dest=off)

    body_rot=pose.get('body_rot',0.0)
    body_y  =pose.get('body_y',0.0)
    torso_pivot=PARTS_IMG['torso']['pivot']

    def body_tf(layer,pivot,ang):
        """Apply the part's own rotation, then the whole-body rotation/offset."""
        l=_rot_about(layer,pivot,ang)
        l=_rot_about(l,torso_pivot,body_rot,(0,-body_y))
        return l

    # torso is the full base; limbs ride on top of it
    place(body_tf(PARTS_IMG['torso']['img'],torso_pivot,0))
    place(body_tf(PARTS_IMG['leg_r']['img'],PARTS_IMG['leg_r']['pivot'],pose.get('leg_r',0)))
    place(body_tf(PARTS_IMG['leg_l']['img'],PARTS_IMG['leg_l']['pivot'],pose.get('leg_l',0)))
    place(body_tf(PARTS_IMG['arm_r']['img'],PARTS_IMG['arm_r']['pivot'],pose.get('arm_r',0)))
    place(body_tf(PARTS_IMG['arm_l']['img'],PARTS_IMG['arm_l']['pivot'],pose.get('arm_l',0)))

    # head (with face drawn in head-local space, then transformed together)
    head=PARTS_IMG['head']['img'].copy()
    face=Image.new('RGBA',BASE.size,(0,0,0,0))
    draw_face(face,pose)
    head.alpha_composite(face)
    hl=_rot_about(head,PARTS_IMG['head']['pivot'],pose.get('head_rot',0),
                  (0,-pose.get('head_y',0)))
    hl=_rot_about(hl,torso_pivot,body_rot,(0,-body_y))
    place(hl)

    if scale!=1.0:
        canvas=canvas.resize((int(W2*scale),int(H2*scale)),Image.LANCZOS)
    return canvas

# ── ANIMATION CHANNELS ───────────────────────────────────────────────────────
def pose_idle(t):
    """Gentle breathing idle."""
    return dict(body_y=math.sin(t*1.9)*3.0, body_rot=math.sin(t*1.4)*0.7,
                head_rot=math.sin(t*1.1)*1.6, head_y=math.sin(t*1.9)*2.0,
                arm_l=math.sin(t*1.5)*2.5, arm_r=-math.sin(t*1.5)*2.5,
                leg_l=0, leg_r=0)

def pose_walk(t, speed=2.2):
    """Walk cycle: opposing arms/legs, body bob at 2x stride."""
    p=t*speed*2*math.pi
    return dict(body_y=abs(math.sin(p))*6.0-2.5, body_rot=math.sin(p)*1.2,
                head_rot=math.sin(p)*1.6, head_y=abs(math.sin(p))*2.5,
                arm_l=math.sin(p)*13, arm_r=-math.sin(p)*13,
                leg_l=-math.sin(p)*10, leg_r=math.sin(p)*10)

def pose_lookup(t, amount=1.0):
    """Tilt the head up in wonder."""
    e=min(1.0,t/0.8)*amount
    return dict(body_y=math.sin(t*1.7)*2.0, body_rot=-1.2*e,
                head_rot=-13*e, head_y=-4*e,
                arm_l=-6*e, arm_r=6*e, leg_l=0, leg_r=0)

def pose_wonder(t):
    """Arms drifting out, leaning back slightly."""
    e=min(1.0,t/1.0)
    return dict(body_y=math.sin(t*1.6)*2.5, body_rot=-2.0*e,
                head_rot=-9*e+math.sin(t*1.3)*1.5, head_y=-3*e,
                arm_l=-30*e, arm_r=30*e, leg_l=0, leg_r=0)

def blink_at(t, period=3.4):
    """Return blink 0..1 with a fast close/open."""
    ph=(t%period)/period
    if ph>0.965: return min(1.0,(ph-0.965)/0.017)
    if ph>0.948: return max(0.0,1-(0.965-ph)/0.017)
    return 0.0
