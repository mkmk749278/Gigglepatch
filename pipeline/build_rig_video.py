#!/usr/bin/env python3
"""
Midnight Market — rigged build.
One Kiran asset, posed every frame (game-style), composited onto Flux plates.
Lip sync is driven by the real voiceover waveform.
"""
import os, math, subprocess, shutil
import numpy as np
import soundfile as sf
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import imageio_ffmpeg
import kiran_rig as K
import door_fx as DFX

SP='/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
KF=os.path.join(SP,'kf')
OUT=os.path.join(SP,'rigwork'); shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
MUSIC='/root/.claude/uploads/eee1d25c-91e0-5fd5-8a12-02f94c656abc/facc5156-Midnight_Bazaar.mp3'
F=imageio_ffmpeg.get_ffmpeg_exe()
FPS,W,H=30,1280,720
FB='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FR='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

# ── VOICEOVER ────────────────────────────────────────────────────────────────
LINES=[
 (1.0 ,"Every city keeps a secret."),
 (5.2 ,"Kiran is the only one who can see it."),
 (10.0,"Every night, at exactly midnight..."),
 (16.5,"something begins to open."),
 (24.0,"A door that was never there before."),
 (31.0,"And something is waiting on the other side."),
 (39.0,"The Midnight Market is open."),
]
TOTAL=46.0

def build_vo():
    from kokoro_onnx import Kokoro
    ko=Kokoro(os.path.join(SP,'kokoro-v1.0.onnx'),os.path.join(SP,'voices-v1.0.bin'))
    SR=24000
    buf=np.zeros(int(SR*(TOTAL+1)),dtype=np.float32)
    spans=[]
    for st,tx in LINES:
        sm,sr=ko.create(tx,voice='am_liam',speed=0.90,lang='en-us')
        if sr!=SR:
            n=int(len(sm)*SR/sr)
            sm=np.interp(np.linspace(0,len(sm)-1,n),np.arange(len(sm)),sm).astype(np.float32)
        i0=int(st*SR); i1=min(i0+len(sm),len(buf))
        buf[i0:i1]+=sm[:i1-i0]*0.95
        spans.append((st,st+len(sm)/SR,tx))
        print(f'  {st:5.1f}s  "{tx}"')
    p=os.path.join(SP,'vo_rig.wav'); sf.write(p,np.clip(buf,-1,1),SR)
    # amplitude envelope -> mouth openness, sampled per video frame
    env=np.zeros(int(TOTAL*FPS)+2,dtype=np.float32)
    win=int(SR/FPS)
    for i in range(len(env)):
        a=i*win; b=min(a+win,len(buf))
        if b>a: env[i]=float(np.sqrt(np.mean(buf[a:b]**2)))
    if env.max()>0: env=env/env.max()
    env=np.clip(env*2.3,0,1)**0.75          # lift quiet consonants
    return p,spans,env

print('Voiceover...')
VO_PATH,SPANS,ENV=build_vo()

def mouth_at(f):
    return float(ENV[min(f,len(ENV)-1)])

# ── PLATES ───────────────────────────────────────────────────────────────────
def plate(name):
    im=Image.open(os.path.join(KF,f'{name}.jpg')).convert('RGB').resize((W,H),Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(radius=1.4,percent=110,threshold=3))
    return ImageEnhance.Color(im).enhance(1.08)

BG_STREET=plate('s1_b')
BG_ALLEY =plate('s5_c')
BG_MARKET=plate('s11_b')

def cam(img,z,dx=0.0,dy=0.0):
    """Crop-zoom a plate: z>1 zooms in; dx/dy are fractional pans."""
    cw,ch=int(W/z),int(H/z)
    cx=int((W-cw)/2+dx*(W-cw)); cy=int((H-ch)/2+dy*(H-ch))
    cx=max(0,min(W-cw,cx)); cy=max(0,min(H-ch,cy))
    return img.crop((cx,cy,cx+cw,cy+ch)).resize((W,H),Image.LANCZOS)

def shadow(canvas,cx,by,rx,ry,strength=110):
    sh=Image.new('RGBA',(W,H),(0,0,0,0))
    ImageDraw.Draw(sh).ellipse([cx-rx,by-ry,cx+rx,by+ry],fill=(0,0,0,strength))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))

def put_char(canvas,pose,scale,foot_x,foot_y,tint=None,tint_a=0.0):
    """Render the rig and place it so the feet land at (foot_x, foot_y)."""
    ch=K.render_pose(pose,scale=scale)
    cw,chh=ch.size
    # feet sit at the bottom of the base area (canvas_pad=180 at that scale)
    pad=int(180*scale)
    x=int(foot_x-cw/2); y=int(foot_y-(chh-pad))
    shadow(canvas,int(foot_x),int(foot_y-6),int(150*scale),int(26*scale))
    if tint and tint_a>0:
        ov=Image.new('RGBA',ch.size,(*tint,0))
        a=(np.array(ch)[:,:,3]*tint_a).astype(np.uint8)
        ov.putalpha(Image.fromarray(a))
        ch=Image.alpha_composite(ch,ov)
    canvas.alpha_composite(ch,dest=(x,y))

def subtitle(canvas,text,alpha):
    if alpha<=0: return
    ol=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ol)
    fn=ImageFont.truetype(FR,31)
    bb=d.textbbox((0,0),text,font=fn); tw=bb[2]-bb[0]
    tx=(W-tw)//2; ty=H-96
    d.rounded_rectangle([tx-22,ty-10,tx+tw+22,ty+bb[3]-bb[1]+12],radius=13,
                        fill=(0,0,0,int(alpha*0.52)))
    d.text((tx+2,ty+2),text,font=fn,fill=(0,0,0,int(alpha*0.75)))
    d.text((tx,ty),text,font=fn,fill=(255,255,255,int(alpha)))
    canvas.alpha_composite(ol)

# ── SCENE TIMELINE ───────────────────────────────────────────────────────────
# (start, end) in seconds
SC=[('street', 0.0, 10.0),
    ('approach',10.0,16.5),
    ('trace', 16.5,24.0),
    ('erupt', 24.0,27.5),
    ('awe',   27.5,34.0),
    ('open',  34.0,37.5),
    ('market',37.5,42.0),
    ('title', 42.0,46.0)]

def scene_at(t):
    for n,a,b in SC:
        if a<=t<b: return n,(t-a),(b-a)
    return SC[-1][0],t-SC[-1][1],SC[-1][2]-SC[-1][1]

FD=os.path.join(OUT,'frames'); os.makedirs(FD)
NF=int(TOTAL*FPS)
print(f'Rendering {NF} frames...')

for f in range(NF):
    t=f/FPS
    name,st,dur=scene_at(t)
    p=st/dur    # progress within scene

    if name=='street':
        bg=cam(BG_STREET,1.02+0.10*p)
        cv=bg.convert('RGBA')
        pose=K.pose_walk(st,speed=1.05)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth_at(f)
        # walks from far/small toward camera
        sc=0.16+0.16*p
        put_char(cv,pose,sc,W*0.5,H*0.60+H*0.26*p)

    elif name=='approach':
        bg=cam(BG_ALLEY,1.00+0.06*p)
        cv=bg.convert('RGBA')
        if p<0.45:
            pose=K.pose_walk(st,speed=1.0)
        else:
            pose=K.pose_lookup(st-dur*0.45,amount=1.0)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth_at(f)
        put_char(cv,pose,0.34,W*0.50,H*0.93)

    elif name=='trace':
        bg=cam(BG_ALLEY,1.06+0.05*p)
        cv=DFX.trace_frame(bg,min(1.0,p*1.12)).convert('RGBA')
        pose=K.pose_lookup(st+1.0,amount=1.0)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth_at(f)
        put_char(cv,pose,0.34,W*0.50,H*0.93,tint=(30,240,215),tint_a=0.16*p)

    elif name=='erupt':
        bg=cam(BG_ALLEY,1.11+0.09*p)
        cv=DFX.erupt_frame(bg,p).convert('RGBA')
        pose=K.pose_wonder(st)
        pose['blink']=0.0; pose['mouth']=max(mouth_at(f),0.35 if p<0.3 else 0.0)
        put_char(cv,pose,0.35,W*0.50,H*0.94,tint=(120,255,240),tint_a=0.30+0.22*(1-p))

    elif name=='awe':
        bg=cam(BG_ALLEY,1.20-0.05*p)
        cv=DFX.open_frame(bg,st*0.5).convert('RGBA')
        pose=K.pose_wonder(2.0+st*0.25)
        pose['blink']=K.blink_at(st); pose['mouth']=mouth_at(f)
        put_char(cv,pose,0.36,W*0.50,H*0.94,tint=(60,235,220),tint_a=0.26)

    elif name=='open':
        bg=cam(BG_ALLEY,1.15-0.06*p)
        cv=DFX.open_frame(bg,3.0+st*0.5).convert('RGBA')
        pose=K.pose_idle(st*1.2)
        pose['head_rot']=-6.0; pose['blink']=K.blink_at(st); pose['mouth']=mouth_at(f)
        put_char(cv,pose,0.36,W*0.50,H*0.94,tint=(255,200,120),tint_a=0.24)

    elif name=='market':
        cv=cam(BG_MARKET,1.16-0.14*p).convert('RGBA')

    else:  # title
        base=cam(BG_MARKET,1.02+0.06*p)
        cv=Image.blend(base,Image.new('RGB',(W,H),(5,4,20)),0.52+0.24*min(p*2,1)).convert('RGBA')
        d=ImageDraw.Draw(cv)
        d.text((W//2,H//2-38),'THE MIDNIGHT MARKET',font=ImageFont.truetype(FB,58),
               fill=(35,240,215),anchor='mm')
        d.text((W//2,H//2+20),'Episode 1  ·  The First Door',font=ImageFont.truetype(FR,27),
               fill=(238,238,242),anchor='mm')
        d.line([(W//2-225,H//2+48),(W//2+225,H//2+48)],fill=(35,240,215),width=2)
        d.text((W//2,H-54),'GigglePatch',font=ImageFont.truetype(FB,29),
               fill=(205,205,215),anchor='mm')

    if name!='title':
        for (a,b,tx) in SPANS:
            if a<=t<=b+0.25:
                fi=min(1.0,(t-a)/0.18); fo=min(1.0,(b+0.25-t)/0.22)
                subtitle(cv,tx,int(max(0.0,min(fi,fo))*255)); break

    cv.convert('RGB').save(os.path.join(FD,f'{f:05d}.png'))
    if f%150==0: print(f'  {f}/{NF} ({100*f//NF}%)')

print('Encoding...')
raw=os.path.join(SP,'ep01_rig_raw.mp4')
subprocess.run([F,'-y','-framerate',str(FPS),'-i',os.path.join(FD,'%05d.png'),
    '-c:v','libx264','-crf','19','-preset','medium','-pix_fmt','yuv420p',raw],
    capture_output=True)

# ── SFX ──────────────────────────────────────────────────────────────────────
SR2=44100; ab=np.zeros(int(SR2*(TOTAL+1)),dtype=np.float32)
rng=np.random.default_rng(11)
n=len(ab); wnd=rng.normal(0,1,n).astype(np.float32)
k=900; c=np.cumsum(wnd); wnd=(c[k:]-c[:-k])/k; wnd=np.pad(wnd,(0,n-len(wnd)))
ab+=wnd*0.04
def place(sig,at):
    i0=int(at*SR2); i1=min(i0+len(sig),len(ab)); ab[i0:i1]+=sig[:i1-i0]
def impact(at,amp=0.9):
    d=int(SR2*2.4); tt=np.arange(d)/SR2; e=np.exp(-tt*2.4)
    s=(np.sin(2*np.pi*44*tt)*0.7+np.sin(2*np.pi*66*tt)*0.3)*e
    s+=rng.normal(0,1,d)*np.exp(-tt*12)*0.22; place(s.astype(np.float32)*amp,at)
def shim(at,amp=0.26):
    d=int(SR2*2.0); tt=np.arange(d)/SR2; e=np.exp(-tt*1.7); s=np.zeros(d)
    for f0 in (1300,1800,2500,3200,4000,4700):
        s+=np.sin(2*np.pi*f0*tt+rng.random()*6)*rng.uniform(.4,1)
    place((s/6*e).astype(np.float32)*amp,at)
def whoosh(at,amp=0.15):
    d=int(SR2*1.5); tt=np.arange(d)/SR2
    e=np.sin(np.pi*np.clip(tt/(d/SR2),0,1))**2
    place((rng.normal(0,1,d)*e).astype(np.float32)*amp,at)
whoosh(17.0); shim(18.4); shim(21.0)
impact(24.1,1.0); shim(24.6,0.32)
shim(34.3,0.26); whoosh(37.6); impact(37.9,0.7)
sfxp=os.path.join(SP,'sfx_rig.wav'); sf.write(sfxp,np.clip(ab,-1,1),SR2)

print('Mix...')
final=os.path.join(SP,'ep01_rig_final.mp4')
r=subprocess.run([F,'-y','-i',raw,'-i',VO_PATH,'-i',sfxp,'-i',MUSIC,'-filter_complex',
 '[1:a]volume=1.0,aresample=48000[vo];[2:a]volume=0.8,aresample=48000[sx];'
 '[3:a]volume=0.18,aresample=48000[mu];'
 '[vo][sx][mu]amix=inputs=3:duration=first:dropout_transition=0,alimiter=limit=0.95[a]',
 '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',final],
 capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-500:]); raise SystemExit(1)
print(f'DONE {final}  {os.path.getsize(final)/1024/1024:.1f}MB')
