#!/usr/bin/env python3
"""
Midnight Market — Ep01, rigged build v2.
Side rig (2-segment legs) for walking; front rig for reactions.
Translation is matched to stride length so the feet do not skate.
"""
import os, math, subprocess, shutil
import numpy as np
import soundfile as sf
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import imageio_ffmpeg
import side_rig as S
import kiran_rig as K
import door_fx as DFX

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
KF=os.path.join(SP,'kf')
OUT=os.path.join(SP,'v2work'); shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
MUSIC='/root/.claude/uploads/eee1d25c-91e0-5fd5-8a12-02f94c656abc/facc5156-Midnight_Bazaar.mp3'
F=imageio_ffmpeg.get_ffmpeg_exe()
FPS,W,H=30,1280,720
FB='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FR='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
TOTAL=48.0

LINES=[
 (1.2 ,"Every city keeps a secret."),
 (6.0 ,"Kiran is the only one who can see it."),
 (12.0,"Every night, at exactly midnight..."),
 (18.5,"something begins to open."),
 (26.0,"A door that was never there before."),
 (33.0,"And something is waiting on the other side."),
 (41.0,"The Midnight Market is open."),
]

print('Voiceover...')
from kokoro_onnx import Kokoro
ko=Kokoro(os.path.join(SP,'kokoro-v1.0.onnx'),os.path.join(SP,'voices-v1.0.bin'))
SR=24000
vbuf=np.zeros(int(SR*(TOTAL+1)),dtype=np.float32); SPANS=[]
for st,tx in LINES:
    sm,sr=ko.create(tx,voice='am_liam',speed=0.90,lang='en-us')
    if sr!=SR:
        n=int(len(sm)*SR/sr)
        sm=np.interp(np.linspace(0,len(sm)-1,n),np.arange(len(sm)),sm).astype(np.float32)
    i0=int(st*SR); i1=min(i0+len(sm),len(vbuf)); vbuf[i0:i1]+=sm[:i1-i0]*0.95
    SPANS.append((st,st+len(sm)/SR,tx)); print(f'  {st:5.1f}s  "{tx}"')
VO=os.path.join(SP,'vo_v2.wav'); sf.write(VO,np.clip(vbuf,-1,1),SR)
ENV=np.zeros(int(TOTAL*FPS)+2,dtype=np.float32); win=int(SR/FPS)
for i in range(len(ENV)):
    a=i*win; b=min(a+win,len(vbuf))
    if b>a: ENV[i]=float(np.sqrt(np.mean(vbuf[a:b]**2)))
if ENV.max()>0: ENV/=ENV.max()
ENV=np.clip(ENV*2.3,0,1)**0.75
def mouth(f): return float(ENV[min(f,len(ENV)-1)])

def plate(n):
    im=Image.open(os.path.join(KF,f'{n}.jpg')).convert('RGB').resize((W,H),Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(radius=1.4,percent=110,threshold=3))
    return ImageEnhance.Color(im).enhance(1.08)
BG_ST=plate('s1_b'); BG_AL=plate('s5_c'); BG_MK=plate('s11_b')

def cam(img,z,dx=0.0,dy=0.0):
    cw,ch=int(W/z),int(H/z)
    cx=int((W-cw)/2+dx*(W-cw)); cy=int((H-ch)/2+dy*(H-ch))
    cx=max(0,min(W-cw,cx)); cy=max(0,min(H-ch,cy))
    return img.crop((cx,cy,cx+cw,cy+ch)).resize((W,H),Image.LANCZOS)

def shadow(cv,cx,by,rx,ry,a=115):
    sh=Image.new('RGBA',(W,H),(0,0,0,0))
    ImageDraw.Draw(sh).ellipse([cx-rx,by-ry,cx+rx,by+ry],fill=(0,0,0,a))
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(17)))

def tint_img(ch,col,a):
    if a<=0: return ch
    ov=Image.new('RGBA',ch.size,(*col,0))
    ov.putalpha(Image.fromarray((np.array(ch)[:,:,3]*a).astype(np.uint8)))
    return Image.alpha_composite(ch,ov)

# ── SIDE-RIG WALK with stride-matched travel ────────────────────────────────
LEG_LEN=295.0          # hip(605) -> foot(900) in side-rig units
SWING  =26.0           # degrees, matches side_rig.walk
SPEED  =0.70           # cycles/sec — a calm night amble, keeps him on screen
STEP_PX=2*LEG_LEN*math.sin(math.radians(SWING))   # horizontal travel per step
PX_PER_SEC=STEP_PX*2*SPEED                        # 2 steps per cycle

def put_side(cv,t,scale,foot_y,x_center,tint=None,ta=0.0,blink=True,mo=0.0):
    pose=S.walk(t,speed=SPEED)
    pose['blink']=S.blink_at(t) if blink else 0.0
    pose['mouth']=mo
    ch=S.render(pose,scale=scale)
    cw,chh=ch.size; pad=int(S.PAD*scale)
    if tint: ch=tint_img(ch,tint,ta)
    shadow(cv,int(x_center),int(foot_y-5),int(120*scale),int(22*scale))
    cv.alpha_composite(ch,dest=(int(x_center-cw/2),int(foot_y-(chh-pad))))

def put_front(cv,pose,scale,fx,fy,tint=None,ta=0.0):
    ch=K.render_pose(pose,scale=scale)
    cw,chh=ch.size; pad=int(180*scale)
    if tint: ch=tint_img(ch,tint,ta)
    shadow(cv,int(fx),int(fy-6),int(150*scale),int(26*scale))
    cv.alpha_composite(ch,dest=(int(fx-cw/2),int(fy-(chh-pad))))

def subtitle(cv,text,alpha):
    if alpha<=0: return
    ol=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ol)
    fn=ImageFont.truetype(FR,31)
    bb=d.textbbox((0,0),text,font=fn); tw=bb[2]-bb[0]
    tx=(W-tw)//2; ty=H-96
    d.rounded_rectangle([tx-22,ty-10,tx+tw+22,ty+bb[3]-bb[1]+12],radius=13,fill=(0,0,0,int(alpha*0.52)))
    d.text((tx+2,ty+2),text,font=fn,fill=(0,0,0,int(alpha*0.75)))
    d.text((tx,ty),text,font=fn,fill=(255,255,255,int(alpha)))
    cv.alpha_composite(ol)

SC=[('walk_st',0.0,10.5),('walk_al',10.5,16.0),('lookup',16.0,18.5),
    ('trace',18.5,26.0),('erupt',26.0,29.5),('awe',29.5,36.0),
    ('open',36.0,39.5),('market',39.5,44.0),('title',44.0,48.0)]
def scene(t):
    for n,a,b in SC:
        if a<=t<b: return n,t-a,b-a
    return SC[-1][0],t-SC[-1][1],SC[-1][2]-SC[-1][1]

FD=os.path.join(OUT,'frames'); os.makedirs(FD)
NF=int(TOTAL*FPS)
print(f'Rendering {NF} frames...')

for f in range(NF):
    t=f/FPS; name,st,dur=scene(t); p=st/dur

    if name=='walk_st':
        # camera eases left with him so he never leaves frame
        cv=cam(BG_ST,1.08,dx=0.68-0.46*p).convert('RGBA')
        sc=0.30
        # ground travel exactly matches stride; camera absorbs part of it
        x=W*1.06-PX_PER_SEC*sc*st+ (W*0.16)*p
        put_side(cv,st,sc,H*0.965,x,mo=mouth(f))

    elif name=='walk_al':
        cv=cam(BG_AL,1.02+0.05*p).convert('RGBA')
        sc=0.34+0.05*p
        x=W*1.02-PX_PER_SEC*sc*st
        x=max(x,W*0.50)                      # settles at centre
        put_side(cv,st,sc,H*0.955,x,mo=mouth(f))

    elif name=='lookup':
        cv=cam(BG_AL,1.07+0.03*p).convert('RGBA')
        pose=K.pose_lookup(st*1.6,amount=1.0)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth(f)
        put_front(cv,pose,0.36,W*0.50,H*0.95)

    elif name=='trace':
        cv=DFX.trace_frame(cam(BG_AL,1.09+0.05*p),min(1.0,p*1.12)).convert('RGBA')
        pose=K.pose_lookup(2.0,amount=1.0)
        pose['body_y']=math.sin(st*1.8)*2.0
        pose['blink']=K.blink_at(st); pose['mouth']=mouth(f)
        put_front(cv,pose,0.36,W*0.50,H*0.95,tint=(30,240,215),ta=0.16*p)

    elif name=='erupt':
        cv=DFX.erupt_frame(cam(BG_AL,1.14+0.08*p),p).convert('RGBA')
        pose=K.pose_wonder(st)
        pose['blink']=0.0; pose['mouth']=max(mouth(f),0.4 if p<0.28 else 0.0)
        put_front(cv,pose,0.37,W*0.50,H*0.955,tint=(120,255,240),ta=0.30+0.22*(1-p))

    elif name=='awe':
        cv=DFX.open_frame(cam(BG_AL,1.22-0.06*p),st*0.5).convert('RGBA')
        pose=K.pose_wonder(2.0+st*0.22)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth(f)
        put_front(cv,pose,0.37,W*0.50,H*0.955,tint=(60,235,220),ta=0.26)

    elif name=='open':
        cv=DFX.open_frame(cam(BG_AL,1.16-0.05*p),3.0+st*0.5).convert('RGBA')
        pose=K.pose_idle(st*1.2); pose['head_rot']=-6.0
        pose['blink']=K.blink_at(st); pose['mouth']=mouth(f)
        put_front(cv,pose,0.37,W*0.50,H*0.955,tint=(255,200,120),ta=0.24)

    elif name=='market':
        cv=cam(BG_MK,1.18-0.16*p).convert('RGBA')

    else:
        base=cam(BG_MK,1.02+0.06*p)
        cv=Image.blend(base,Image.new('RGB',(W,H),(5,4,20)),0.52+0.24*min(p*2,1)).convert('RGBA')
        d=ImageDraw.Draw(cv)
        d.text((W//2,H//2-38),'THE MIDNIGHT MARKET',font=ImageFont.truetype(FB,58),fill=(35,240,215),anchor='mm')
        d.text((W//2,H//2+20),'Episode 1  ·  The First Door',font=ImageFont.truetype(FR,27),fill=(238,238,242),anchor='mm')
        d.line([(W//2-225,H//2+48),(W//2+225,H//2+48)],fill=(35,240,215),width=2)
        d.text((W//2,H-54),'GigglePatch',font=ImageFont.truetype(FB,29),fill=(205,205,215),anchor='mm')

    if name!='title':
        for (a,b,tx) in SPANS:
            if a<=t<=b+0.25:
                fi=min(1.0,(t-a)/0.18); fo=min(1.0,(b+0.25-t)/0.22)
                subtitle(cv,tx,int(max(0.0,min(fi,fo))*255)); break

    cv.convert('RGB').save(os.path.join(FD,f'{f:05d}.png'))
    if f%180==0: print(f'  {f}/{NF} ({100*f//NF}%)')

print('Encoding...')
raw=os.path.join(SP,'ep01_v2r_raw.mp4')
subprocess.run([F,'-y','-framerate',str(FPS),'-i',os.path.join(FD,'%05d.png'),
    '-c:v','libx264','-crf','19','-preset','medium','-pix_fmt','yuv420p',raw],capture_output=True)

SR2=44100; ab=np.zeros(int(SR2*(TOTAL+1)),dtype=np.float32)
rng=np.random.default_rng(11)
n=len(ab); wn=rng.normal(0,1,n).astype(np.float32)
k=900; c=np.cumsum(wn); wn=(c[k:]-c[:-k])/k; wn=np.pad(wn,(0,n-len(wn)))
ab+=wn*0.04
def place(s,at):
    i0=int(at*SR2); i1=min(i0+len(s),len(ab)); ab[i0:i1]+=s[:i1-i0]
def impact(at,amp=0.9):
    d=int(SR2*2.4); tt=np.arange(d)/SR2; e=np.exp(-tt*2.4)
    s=(np.sin(2*np.pi*44*tt)*0.7+np.sin(2*np.pi*66*tt)*0.3)*e
    s+=rng.normal(0,1,d)*np.exp(-tt*12)*0.22; place(s.astype(np.float32)*amp,at)
def shim(at,amp=0.26):
    d=int(SR2*2.0); tt=np.arange(d)/SR2; e=np.exp(-tt*1.7); s=np.zeros(d)
    for f0 in (1300,1800,2500,3200,4000,4700): s+=np.sin(2*np.pi*f0*tt+rng.random()*6)*rng.uniform(.4,1)
    place((s/6*e).astype(np.float32)*amp,at)
def whoosh(at,amp=0.15):
    d=int(SR2*1.5); tt=np.arange(d)/SR2
    e=np.sin(np.pi*np.clip(tt/(d/SR2),0,1))**2
    place((rng.normal(0,1,d)*e).astype(np.float32)*amp,at)
def step(at,amp=0.10):
    d=int(SR2*0.28); tt=np.arange(d)/SR2; e=np.exp(-tt*26)
    s=rng.normal(0,1,d)*e+np.sin(2*np.pi*95*tt)*e*0.5
    place(s.astype(np.float32)*amp,at)
# footsteps across both walking scenes, on stride contacts
tt=0.30
while tt<16.0:
    if tt>10.5 or tt<10.5: step(tt,0.085 if tt<10.5 else 0.11)
    tt+=1.0/(SPEED*2)
whoosh(19.0); shim(20.6); shim(23.4)
impact(26.1,1.0); shim(26.6,0.32); shim(36.3,0.26); whoosh(39.6); impact(39.9,0.7)
SFX=os.path.join(SP,'sfx_v2.wav'); sf.write(SFX,np.clip(ab,-1,1),SR2)

print('Mix...')
final=os.path.join(SP,'ep01_v2r_final.mp4')
r=subprocess.run([F,'-y','-i',raw,'-i',VO,'-i',SFX,'-i',MUSIC,'-filter_complex',
 '[1:a]volume=1.0,aresample=48000[vo];[2:a]volume=0.85,aresample=48000[sx];'
 '[3:a]volume=0.18,aresample=48000[mu];'
 '[vo][sx][mu]amix=inputs=3:duration=first:dropout_transition=0,alimiter=limit=0.95[a]',
 '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',final],
 capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-500:]); raise SystemExit(1)
print(f'DONE {final}  {os.path.getsize(final)/1024/1024:.1f}MB')
