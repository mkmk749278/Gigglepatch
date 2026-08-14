#!/usr/bin/env python3
"""
Kiran side rig v2 — animation-principles pass.

  * 2-bone IK legs: the foot is PINNED to the ground during stance and the
    hip/knee angles are solved backwards from it (no skating, real weight).
  * Ankle/boot as its own segment: stays level on the ground, rolls in swing.
  * Overlapping action: chest, head, ears and tail each lag the hips.
  * Ease curves instead of raw sine.
  * Squash/stretch + weight shift over the planted foot.
"""
import numpy as np, math, os
from PIL import Image, ImageDraw, ImageFilter

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
BASE=Image.open(os.path.join(SP,'kiran_side.png')).convert('RGBA')
BW,BH=BASE.size                     # 244 x 900

# ── SKELETON (measured off the reference grid) ──────────────────────────────
HIP  =(105.0,605.0)
KNEE =(103.0,735.0)
ANKLE=(100.0,805.0)
SOLE_Y=900.0
SHLD =(95.0,352.0)
NECK =(105.0,288.0)
L1=math.dist(HIP,KNEE)              # thigh ~130
L2=math.dist(KNEE,(ANKLE[0],SOLE_Y))# shin+boot to sole ~165
LEG=L1+L2                           # ~295

REG=dict(
 head =(8,   0, 205, 302),
 torso=(28, 236, 205, 640),
 arm  =(44, 330, 130, 585),
 thigh=(44, 588, 170, 752),
 shin =(30, 716, 170, 812),
 boot =(28, 782, 175, 900),
 tail =(138,575, 244, 712),
)
def _mask(box,f=7):
    m=Image.new('L',(BW,BH),0); ImageDraw.Draw(m).rectangle(box,fill=255)
    return m.filter(ImageFilter.GaussianBlur(f))
def _layer(box):
    l=Image.new('RGBA',(BW,BH),(0,0,0,0)); l.paste(BASE,(0,0),_mask(box)); return l
L={k:_layer(v) for k,v in REG.items()}
def _dark(img,f=0.60):
    a=np.array(img).astype(np.float32); a[:,:,:3]*=f
    return Image.fromarray(a.clip(0,255).astype(np.uint8),'RGBA')
for k in ('thigh','shin','boot','arm'):
    L[k+'_far']=_dark(L[k])
_t=np.array(L['torso']).copy(); _t[:250,:,3]=0
L['torso']=Image.fromarray(_t,'RGBA')

PAD=280
CW,CH=BW+PAD*2,BH+PAD*2

def _rot(layer,pivot,ang,off=(0,0)):
    if abs(ang)<0.01 and off==(0,0): return layer
    out=layer.rotate(ang,resample=Image.BICUBIC,center=pivot)
    if off!=(0,0):
        out=out.transform(out.size,Image.AFFINE,(1,0,-off[0],0,1,-off[1]),resample=Image.BICUBIC)
    return out

# ── EASING ───────────────────────────────────────────────────────────────────
def ease_io(x):                       # smooth acceleration + deceleration
    x=min(1.0,max(0.0,x)); return x*x*(3-2*x)
def ease_out(x):
    x=min(1.0,max(0.0,x)); return 1-(1-x)**2.2

# ── GAIT ─────────────────────────────────────────────────────────────────────
STANCE=0.62            # fraction of the cycle the foot is on the ground
STRIDE=140.0           # ground distance covered while a foot is planted
LIFT  =52.0            # peak foot lift during swing
DIST_PER_CYCLE=STRIDE/STANCE          # body travel per full cycle

def foot_local(u):
    """
    Foot position relative to the hip, in rig units, for cycle phase u in [0,1).
    Stance: foot pinned to ground, sliding backward relative to the body.
    Swing : arcs forward and lifts.
    """
    u=u%1.0
    if u<STANCE:
        s=u/STANCE
        fx= STRIDE*0.5-STRIDE*s               # linear: ground is not accelerating
        fy= LEG
    else:
        s=(u-STANCE)/(1.0-STANCE)
        se=ease_io(s)
        fx=-STRIDE*0.5+STRIDE*se
        fy= LEG-LIFT*math.sin(math.pi*s)**0.85
    return fx,fy

def solve_ik(fx,fy):
    """
    2-bone IK. Returns (thigh_deg, knee_deg) as deltas from the rest pose
    (rest = leg straight down). Knee bends backwards only.
    """
    d=math.hypot(fx,fy)
    d=min(d,L1+L2-0.6)                       # never fully lock/overextend
    d=max(d,abs(L1-L2)+0.6)
    # angle of the hip->foot line, measured from straight-down (+y)
    base=math.degrees(math.atan2(fx,fy))
    cos_a1=(L1*L1+d*d-L2*L2)/(2*L1*d)
    a1=math.degrees(math.acos(max(-1.0,min(1.0,cos_a1))))
    cos_a2=(L1*L1+L2*L2-d*d)/(2*L1*L2)
    a2=math.degrees(math.acos(max(-1.0,min(1.0,cos_a2))))
    thigh=base+a1                             # PIL rotation is CCW-positive
    knee =-(180.0-a2)                         # interior -> bend
    return thigh,knee

def walk(t, speed=0.85):
    """Full pose for a natural walk at `speed` cycles/second."""
    u=(t*speed)%1.0
    # near leg leads, far leg is half a cycle behind
    fN=foot_local(u);        thN,knN=solve_ik(*fN)
    fF=foot_local(u+0.5);    thF,knF=solve_ik(*fF)

    # boot stays level with the ground, with a heel-toe roll through swing
    def boot_ang(u_,th,kn):
        u_=u_%1.0
        if u_<STANCE:
            s=u_/STANCE
            roll=-7.0*ease_out(max(0.0,(s-0.72)/0.28))     # toe-off
        else:
            s=(u_-STANCE)/(1-STANCE)
            roll=10.0*math.sin(math.pi*s)-4.0*ease_io(s)   # lift toe, then heel strike
        return -(th+kn)+roll
    btN=boot_ang(u,thN,knN); btF=boot_ang(u+0.5,thF,knF)

    # vertical bob: body is lowest just after each contact (2 dips per cycle)
    bob=-5.0*abs(math.sin(math.pi*(u*2)))+2.0
    # weight shift: lean slightly over whichever foot is planted
    lean=1.6*math.sin(2*math.pi*u)
    # squash on impact, stretch at passing
    squash=1.0+0.016*math.cos(2*math.pi*(u*2))

    # ── overlapping action: each part lags the hips ──
    def lag(frames):
        return ((t-frames/30.0)*speed)%1.0
    uc=lag(2); uh=lag(3.5); ue=lag(5); ut=lag(6.5)
    chest = 2.2*math.sin(2*math.pi*uc)
    head  = 2.6*math.sin(2*math.pi*uh+0.4)
    ears  = 4.0*math.sin(2*math.pi*ue+0.8)
    tail  = 7.0*math.sin(2*math.pi*ut)+3.0*math.sin(4*math.pi*ut)

    # arms counter-swing the legs, with a touch of elbow drag
    armN=-15.0*math.sin(2*math.pi*lag(1.5))
    armF= 15.0*math.sin(2*math.pi*lag(1.5))

    return dict(hipN=thN,kneeN=knN,bootN=btN,
                hipF=thF,kneeF=knF,bootF=btF,
                body_y=bob, body_rot=lean, chest=chest,
                head_rot=head, ears=ears, tail=tail,
                armN=armN, armF=armF, squash=squash)

def idle(t):
    b=math.sin(t*1.9)
    return dict(hipN=0,kneeN=0,bootN=0,hipF=0,kneeF=0,bootF=0,
                body_y=b*2.2, body_rot=math.sin(t*1.25)*0.5, chest=math.sin(t*1.7-0.3)*0.8,
                head_rot=math.sin(t*1.0-0.5)*1.3, ears=math.sin(t*1.4-0.9)*2.0,
                tail=4.5*math.sin(t*1.1-1.2),
                armN=math.sin(t*1.5)*1.8, armF=-math.sin(t*1.5)*1.8, squash=1.0)

def blink_at(t,period=3.6):
    ph=(t%period)/period
    if ph>0.965: return min(1.0,(ph-0.965)/0.017)
    if ph>0.948: return max(0.0,1-(0.965-ph)/0.017)
    return 0.0

# ── FACE ─────────────────────────────────────────────────────────────────────
EYE=(55,205); ERX,ERY=15,10
MOUTH=(30,250); MRX=15
def _face(cv,pose):
    bl=pose.get('blink',0.0); mo=pose.get('mouth',0.0)
    if bl>0.05:
        ex,ey=EYE; drop=(2*ERY+4)*bl
        eye=Image.new('L',(BW,BH),0)
        ImageDraw.Draw(eye).ellipse([ex-ERX-2,ey-ERY-2,ex+ERX+2,ey+ERY+2],fill=255)
        cur=Image.new('L',(BW,BH),0); cy=ey-ERY-2+drop
        ImageDraw.Draw(cur).rectangle([ex-ERX-5,ey-ERY-9,ex+ERX+5,cy],fill=255)
        m=Image.fromarray(np.minimum(np.array(eye),np.array(cur))).filter(ImageFilter.GaussianBlur(0.9))
        brow=BASE.crop((ex-ERX-5,max(0,ey-ERY*2-12),ex+ERX+5,max(1,ey-ERY)))
        tmp=Image.new('RGBA',(BW,BH),(0,0,0,0)); tmp.paste(brow,(ex-ERX-5,int(ey-ERY*2-12+drop)))
        cv.paste(tmp,(0,0),m)
    if mo>0.05:
        mx,my=MOUTH; h=2.5+8.0*mo
        m2=Image.new('RGBA',(BW,BH),(0,0,0,0))
        ImageDraw.Draw(m2).ellipse([mx-MRX,my-h*0.3,mx+MRX,my+h],fill=(44,20,20,240))
        cv.alpha_composite(m2.filter(ImageFilter.GaussianBlur(1.3)))

# ── RENDER ───────────────────────────────────────────────────────────────────
BPIV=(105.0,470.0)

def render(pose, scale=1.0):
    cv=Image.new('RGBA',(CW,CH),(0,0,0,0)); dst=(PAD,PAD)
    brot=pose.get('body_rot',0.0); by=pose.get('body_y',0.0)
    chest=pose.get('chest',0.0); sq=pose.get('squash',1.0)

    def carry(l):   # whole-body rotation + bob
        return _rot(l,BPIV,brot,(0,-by))
    def put(l): cv.alpha_composite(l,dest=dst)

    def leg(th_l,sh_l,bt_l,hip,knee,boot):
        th=_rot(th_l,HIP,hip)
        sh=_rot(_rot(sh_l,KNEE,knee),HIP,hip)
        bt=_rot(_rot(_rot(bt_l,ANKLE,boot),KNEE,knee),HIP,hip)
        return th,sh,bt

    # far side
    for l in leg(L['thigh_far'],L['shin_far'],L['boot_far'],
                 pose.get('hipF',0),pose.get('kneeF',0),pose.get('bootF',0)):
        put(carry(l))
    put(carry(_rot(L['arm_far'],SHLD,pose.get('armF',0))))
    put(carry(_rot(L['tail'],(160,630),pose.get('tail',0))))
    # torso (chest counter-rotates a touch)
    put(carry(_rot(L['torso'],(105,560),chest*0.5)))
    # head + ears lag
    head=L['head'].copy()
    face=Image.new('RGBA',(BW,BH),(0,0,0,0)); _face(face,pose); head.alpha_composite(face)
    put(carry(_rot(head,NECK,pose.get('head_rot',0)+pose.get('ears',0)*0.25)))
    # near side
    for l in leg(L['thigh'],L['shin'],L['boot'],
                 pose.get('hipN',0),pose.get('kneeN',0),pose.get('bootN',0)):
        put(carry(l))
    put(carry(_rot(L['arm'],SHLD,pose.get('armN',0))))

    if abs(sq-1.0)>0.002:                       # squash/stretch about the feet
        nh=int(CH*sq); cv=cv.resize((CW,nh),Image.LANCZOS)
        if nh<CH:
            pad=Image.new('RGBA',(CW,CH),(0,0,0,0)); pad.paste(cv,(0,CH-nh)); cv=pad
        else:
            cv=cv.crop((0,nh-CH,CW,nh))
    if scale!=1.0:
        cv=cv.resize((int(CW*scale),int(CH*scale)),Image.LANCZOS)
    return cv

def render_blurred(pose_fn,t,scale=1.0,samples=4,shutter=1/30*0.6):
    """Motion blur: average sub-frames across the shutter interval."""
    if samples<=1: return render(pose_fn(t),scale)
    acc=None
    for i in range(samples):
        tt=t+(i/(samples-1)-0.5)*shutter
        im=np.asarray(render(pose_fn(tt),scale),dtype=np.float32)
        acc=im if acc is None else acc+im
    return Image.fromarray((acc/samples).clip(0,255).astype(np.uint8),'RGBA')
