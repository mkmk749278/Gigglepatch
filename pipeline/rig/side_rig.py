#!/usr/bin/env python3
"""
Kiran side-profile rig with two-segment legs (thigh + shin).
A walk only reads when the knee bends — that is what this adds.
Character faces LEFT; walks in -x.
"""
import numpy as np, math, os
from PIL import Image, ImageDraw, ImageFilter

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
BASE=Image.open(os.path.join(SP,'kiran_side.png')).convert('RGBA')
BW,BH=BASE.size          # 244 x 900

HIP =(105,605)
KNEE=(103,735)
SHLD=(95,352)
NECK=(105,288)

REG=dict(
 head =(8,   0, 205, 302),
 torso=(28, 236, 205, 640),
 arm  =(44, 330, 130, 585),
 thigh=(44, 588, 170, 752),
 shin =(30, 718, 170, 900),
 tail =(138,575, 244, 712),
)

def _mask(box, feather=7):
    m=Image.new('L',(BW,BH),0)
    ImageDraw.Draw(m).rectangle(box,fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))

def _layer(box):
    l=Image.new('RGBA',(BW,BH),(0,0,0,0))
    l.paste(BASE,(0,0),_mask(box))
    return l

L={k:_layer(v) for k,v in REG.items()}

def _dark(img,f=0.62):
    a=np.array(img).astype(np.float32)
    a[:,:,:3]*=f
    return Image.fromarray(a.clip(0,255).astype(np.uint8),'RGBA')

L['thigh_far']=_dark(L['thigh']); L['shin_far']=_dark(L['shin'])
L['arm_far']  =_dark(L['arm'])

# torso base: drop the head so it can turn without ghosting
_t=np.array(L['torso']).copy()
_t[:250,:,3]=0
L['torso']=Image.fromarray(_t,'RGBA')

PAD=260
CW,CH=BW+PAD*2, BH+PAD*2

def _rot(layer,pivot,ang,off=(0,0)):
    if abs(ang)<0.01 and off==(0,0): return layer
    out=layer.rotate(ang,resample=Image.BICUBIC,center=pivot)
    if off!=(0,0):
        out=out.transform(out.size,Image.AFFINE,(1,0,-off[0],0,1,-off[1]),
                          resample=Image.BICUBIC)
    return out

def _leg(thigh_l, shin_l, hip_ang, knee_ang):
    """
    Two-segment leg. The shin inherits the thigh's rotation about the hip,
    then adds its own bend about the knee (which the thigh rotation moved).
    """
    th=_rot(thigh_l,HIP,hip_ang)
    sh=_rot(shin_l,KNEE,knee_ang)      # bend at the knee first
    sh=_rot(sh,HIP,hip_ang)            # then carry with the thigh
    return th,sh

def render(pose, scale=1.0):
    """
    pose: body_y, body_rot, head_rot,
          hipN,kneeN (near leg), hipF,kneeF (far leg),
          armN, armF, tail, blink, mouth
    """
    cv=Image.new('RGBA',(CW,CH),(0,0,0,0))
    dst=(PAD,PAD)
    brot=pose.get('body_rot',0.0); by=pose.get('body_y',0.0)
    BPIV=(105,470)

    def carry(l):
        return _rot(l,BPIV,brot,(0,-by))

    def put(l): cv.alpha_composite(l,dest=dst)

    # far side first
    thF,shF=_leg(L['thigh_far'],L['shin_far'],pose.get('hipF',0),pose.get('kneeF',0))
    put(carry(thF)); put(carry(shF))
    put(carry(_rot(L['arm_far'],SHLD,pose.get('armF',0))))
    # tail behind body
    put(carry(_rot(L['tail'],(160,630),pose.get('tail',0))))
    # torso
    put(carry(L['torso']))
    # head
    head=L['head'].copy()
    face=Image.new('RGBA',(BW,BH),(0,0,0,0))
    _face(face,pose)
    head.alpha_composite(face)
    put(carry(_rot(head,NECK,pose.get('head_rot',0))))
    # near side
    thN,shN=_leg(L['thigh'],L['shin'],pose.get('hipN',0),pose.get('kneeN',0))
    put(carry(thN)); put(carry(shN))
    put(carry(_rot(L['arm'],SHLD,pose.get('armN',0))))

    if scale!=1.0:
        cv=cv.resize((int(CW*scale),int(CH*scale)),Image.LANCZOS)
    return cv

# profile eye / muzzle (from the reference grid)
EYE=(55,205); EYE_RX,EYE_RY=15,10
MOUTH=(30,250); MRX=15
FUR=(206,120,52); FUR_D=(150,80,34)

def _face(cv,pose):
    blink=pose.get('blink',0.0); mouth=pose.get('mouth',0.0)
    if blink>0.05:
        ex,ey=EYE
        drop=(2*EYE_RY+4)*blink
        eye=Image.new('L',(BW,BH),0)
        ImageDraw.Draw(eye).ellipse([ex-EYE_RX-2,ey-EYE_RY-2,ex+EYE_RX+2,ey+EYE_RY+2],fill=255)
        cur=Image.new('L',(BW,BH),0)
        cy=ey-EYE_RY-2+drop
        ImageDraw.Draw(cur).rectangle([ex-EYE_RX-5,ey-EYE_RY-9,ex+EYE_RX+5,cy],fill=255)
        m=Image.fromarray(np.minimum(np.array(eye),np.array(cur))).filter(ImageFilter.GaussianBlur(0.9))
        brow=BASE.crop((ex-EYE_RX-5,max(0,ey-EYE_RY*2-12),ex+EYE_RX+5,max(1,ey-EYE_RY)))
        tmp=Image.new('RGBA',(BW,BH),(0,0,0,0))
        tmp.paste(brow,(ex-EYE_RX-5,int(ey-EYE_RY*2-12+drop)))
        cv.paste(tmp,(0,0),m)
    if mouth>0.05:
        mx,my=MOUTH
        h=2.5+8.0*mouth
        mo=Image.new('RGBA',(BW,BH),(0,0,0,0))
        ImageDraw.Draw(mo).ellipse([mx-MRX,my-h*0.3,mx+MRX,my+h],fill=(44,20,20,240))
        cv.alpha_composite(mo.filter(ImageFilter.GaussianBlur(1.3)))

# ── WALK CYCLE ───────────────────────────────────────────────────────────────
def walk(t, speed=1.35):
    """
    Facing left, so a forward swing is a NEGATIVE rotation.
    Knee bends only one way, peaking through the swing phase.
    """
    p=t*speed*2*math.pi
    def leg(ph):
        hip = -26.0*math.sin(ph)
        knee=  40.0*max(0.0, math.sin(ph-1.25))     # heel tucks during swing
        return hip,knee
    hN,kN=leg(p)
    hF,kF=leg(p+math.pi)
    bob=-4.5*abs(math.cos(p))+2.0                   # lowest at each contact
    return dict(body_y=bob, body_rot=1.1*math.sin(p*2),
                head_rot=1.6*math.sin(p+0.5),
                hipN=hN, kneeN=kN, hipF=hF, kneeF=kF,
                armN=18.0*math.sin(p+math.pi), armF=18.0*math.sin(p),
                tail=6.0*math.sin(p*2))

def idle(t):
    return dict(body_y=math.sin(t*1.9)*2.5, body_rot=math.sin(t*1.3)*0.6,
                head_rot=math.sin(t*1.05)*1.4,
                hipN=0,kneeN=0,hipF=0,kneeF=0,
                armN=math.sin(t*1.5)*2.0, armF=-math.sin(t*1.5)*2.0,
                tail=4.0*math.sin(t*1.2))

def blink_at(t,period=3.6):
    ph=(t%period)/period
    if ph>0.965: return min(1.0,(ph-0.965)/0.017)
    if ph>0.948: return max(0.0,1-(0.965-ph)/0.017)
    return 0.0
