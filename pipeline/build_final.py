#!/usr/bin/env python3
"""
Midnight Market — Ep01 teaser, final build.
Flux plates → motion interpolation → composited door VFX → VO + SFX + music.
"""
import os, subprocess, shutil, math
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import imageio_ffmpeg
import door_fx as DFX

SP    = '/tmp/claude-0/-home-user-Gigglepatch/eee1d25c-91e0-5fd5-8a12-02f94c656abc/scratchpad'
KF    = os.path.join(SP,'kf')
WORK  = os.path.join(SP,'w2')
MUSIC = '/root/.claude/uploads/eee1d25c-91e0-5fd5-8a12-02f94c656abc/facc5156-Midnight_Bazaar.mp3'
F     = imageio_ffmpeg.get_ffmpeg_exe()
FPS,W,H = 30,1280,720
shutil.rmtree(WORK,ignore_errors=True); os.makedirs(WORK)

FB='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FR='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

def enhance(im):
    im=im.filter(ImageFilter.UnsharpMask(radius=1.4,percent=112,threshold=3))
    im=ImageEnhance.Contrast(im).enhance(1.05)
    return ImageEnhance.Color(im).enhance(1.09)

def load(name, crop=None):
    im=Image.open(os.path.join(KF,f'{name}.jpg')).convert('RGB')
    if crop:
        z,cxf,cyf=crop
        cw,ch=int(im.width/z),int(im.height/z)
        cx,cy=int(im.width*cxf),int(im.height*cyf)
        x0=max(0,min(im.width-cw,cx-cw//2)); y0=max(0,min(im.height-ch,cy-ch//2))
        im=im.crop((x0,y0,x0+cw,y0+ch))
    return enhance(im.resize((W,H),Image.LANCZOS))

def encode(frames_dir, out, fps=FPS):
    subprocess.run([F,'-y','-framerate',str(fps),'-i',os.path.join(frames_dir,'%05d.png'),
        '-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p',out],
        capture_output=True)
    return out

# ── interpolated shot from Flux keyframes ────────────────────────────────────
SRC_FPS=2.0   # keyframes are fed at a fixed rate, then time-stretched

def interp_shot(sid, keys, secs, cam='push_slow', crop=None, tint=None):
    d=os.path.join(WORK,sid); shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    imgs=[load(k,crop) for k in keys if os.path.exists(os.path.join(KF,f'{k}.jpg'))]
    if not imgs: return None
    if len(imgs)==1: imgs=imgs*2
    # synthesize blended midpoints: minterpolate needs >=3 source frames
    dense=[]
    for i in range(len(imgs)-1):
        dense.append(imgs[i])
        dense.append(Image.blend(imgs[i],imgs[i+1],0.5))
    dense.append(imgs[-1])
    for i,im in enumerate(dense): im.save(os.path.join(d,f'{i:03d}.png'))
    n=len(dense)

    # interpolate at a sane source rate, then stretch to the target duration
    src_dur=(n-1)/SRC_FPS
    stretch=secs/src_dur
    itp=os.path.join(WORK,f'{sid}_i.mp4')
    vf=(f'minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,'
        f'setpts={stretch:.5f}*PTS,fps={FPS}')
    r=subprocess.run([F,'-y','-framerate',f'{SRC_FPS}','-i',os.path.join(d,'%03d.png'),
        '-vf',vf,'-c:v','libx264','-crf','16','-pix_fmt','yuv420p',itp],
        capture_output=True,text=True)
    if r.returncode!=0:
        print(f'  interp fail {sid}: {r.stderr[-200:]}'); return None

    nf=max(1,int(secs*FPS))
    cxe='iw/2-(iw/zoom/2)'; cye='ih/2-(ih/zoom/2)'
    zm={'push_slow':f'min(pzoom+{0.13/nf:.6f},1.13)',
        'push_fast':f'min(pzoom+{0.24/nf:.6f},1.24)',
        'pull':     f'min(pzoom+{0.15/nf:.6f},1.15)',
        'none':'1.02'}[cam]
    out=os.path.join(WORK,f'{sid}_c.mp4')
    # d=1 : one output frame per input frame (input is video, not a still)
    vf=(f"scale={int(W*1.3)}:{int(H*1.3)},zoompan=z='{zm}':x='{cxe}':y='{cye}'"
        f":d=1:fps={FPS}:s={W}x{H}")
    r=subprocess.run([F,'-y','-i',itp,'-vf',vf,'-t',f'{secs}','-c:v','libx264',
        '-crf','16','-pix_fmt','yuv420p',out],capture_output=True,text=True)
    if r.returncode!=0 or not os.path.exists(out) or os.path.getsize(out)<20000:
        print(f'  cam fallback {sid}'); out=itp
    if cam=='pull':
        rv=os.path.join(WORK,f'{sid}_r.mp4')
        rr=subprocess.run([F,'-y','-i',out,'-vf','reverse','-c:v','libx264','-crf','16',
            '-pix_fmt','yuv420p',rv],capture_output=True)
        if rr.returncode==0 and os.path.getsize(rv)>20000: out=rv
    if tint:
        fd=os.path.join(WORK,f'{sid}_fx'); shutil.rmtree(fd,ignore_errors=True); os.makedirs(fd)
        subprocess.run([F,'-y','-i',out,os.path.join(fd,'%05d.png')],capture_output=True)
        fs=sorted(f for f in os.listdir(fd) if f.endswith('.png'))
        if not fs:
            print(f'  tint skipped {sid} (no frames)'); return out
        col,stre=tint
        for i,fn in enumerate(fs):
            t=i/max(1,len(fs)-1); p=os.path.join(fd,fn)
            im=Image.open(p).convert('RGB')
            g=DFX._spill(W//2,int(H*0.45),460,col,stre*(0.5+0.5*t))
            DFX._screen(im,g).save(p)
        te=encode(fd,os.path.join(WORK,f'{sid}_t.mp4'))
        if os.path.exists(te) and os.path.getsize(te)>20000: out=te
    return out

# ── composited door shots ────────────────────────────────────────────────────
CACHE=os.path.join(SP,'doorcache'); os.makedirs(CACHE,exist_ok=True)

def door_shot(sid, plate_name, mode, secs, zoom_from=1.0, zoom_to=1.10):
    cached=os.path.join(CACHE,f'{sid}.mp4')
    if os.path.exists(cached) and os.path.getsize(cached)>50000:
        print(f'  {sid} cached'); return cached
    plate0=load(plate_name)
    d=os.path.join(WORK,sid); shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    nf=int(secs*FPS)
    for i in range(nf):
        t=i/max(1,nf-1)
        z=zoom_from+(zoom_to-zoom_from)*t
        cw,ch=int(W/z),int(H/z)
        x0,y0=(W-cw)//2,(H-ch)//2
        pl=plate0.crop((x0,y0,x0+cw,y0+ch)).resize((W,H),Image.LANCZOS)
        if   mode=='trace': fr=DFX.trace_frame(pl,t)
        elif mode=='erupt': fr=DFX.erupt_frame(pl,t)
        else:               fr=DFX.open_frame(pl,t)
        fr.save(os.path.join(d,f'{i:05d}.png'))
    encode(d,cached)
    return cached

# ── title ────────────────────────────────────────────────────────────────────
def title_card(secs):
    d=os.path.join(WORK,'title'); os.makedirs(d,exist_ok=True)
    base=load('s11_b')
    nf=int(secs*FPS)
    fb=ImageFont.truetype(FB,58); fs=ImageFont.truetype(FR,27); fc=ImageFont.truetype(FB,29)
    for i in range(nf):
        t=i/nf
        z=1.0+0.06*t; cw,ch=int(W/z),int(H/z)
        im=base.crop(((W-cw)//2,(H-ch)//2,(W-cw)//2+cw,(H-ch)//2+ch)).resize((W,H),Image.LANCZOS)
        im=Image.blend(im,Image.new('RGB',(W,H),(5,4,20)),0.50+0.22*min(t*2,1))
        dr=ImageDraw.Draw(im)
        dr.text((W//2,H//2-38),'THE MIDNIGHT MARKET',font=fb,fill=(35,240,215),anchor='mm')
        dr.text((W//2,H//2+20),'Episode 1  ·  The First Door',font=fs,fill=(238,238,242),anchor='mm')
        dr.line([(W//2-225,H//2+48),(W//2+225,H//2+48)],fill=(35,240,215),width=2)
        dr.text((W//2,H-54),'GigglePatch',font=fc,fill=(205,205,215),anchor='mm')
        im.save(os.path.join(d,f'{i:05d}.png'))
    return encode(d,os.path.join(WORK,'title.mp4'))

# ── TIMELINE ─────────────────────────────────────────────────────────────────
CROP_S2=(1.35,0.52,0.60)   # crop past the background cars
PLAN=[
 ('s1',  lambda: interp_shot('s1', ['s1_a','s1_b'],        4.0,'push_slow')),
 ('s2',  lambda: interp_shot('s2', ['s2_a','s2_b','s2_c'], 5.0,'none',CROP_S2)),
 ('s3',  lambda: interp_shot('s3', ['s3_a','s3_b'],        3.0,'push_slow')),
 ('s4',  lambda: interp_shot('s4', ['s4_a','s4_b'],        3.0,'push_fast',None,((30,240,215),0.20))),
 ('dtr', lambda: door_shot('dtr','s5_c','trace',5.0,1.00,1.08)),
 ('der', lambda: door_shot('der','s5_c','erupt',3.0,1.08,1.20)),
 ('s8',  lambda: interp_shot('s8', ['s8_a','s8_b'],        4.0,'push_slow',None,((30,235,215),0.24))),
 ('dop', lambda: door_shot('dop','s5_c','open', 2.5,1.20,1.14)),
 ('s9',  lambda: interp_shot('s9', ['s9_a','s9_b'],        3.0,'push_slow',None,((255,195,105),0.22))),
 ('s10', lambda: interp_shot('s10',['s10_a','s10_b'],      4.0,'push_slow',None,((255,195,105),0.20))),
 ('s11', lambda: interp_shot('s11',['s11_a','s11_b'],      4.5,'pull')),
]
DUR={'s1':4.0,'s2':5.0,'s3':3.0,'s4':3.0,'dtr':5.0,'der':3.0,'s8':4.0,
     'dop':2.5,'s9':3.0,'s10':4.0,'s11':4.5}
TITLE=4.0

print('Building shots...')
clips=[]; marks={}; tm=0.0
for sid,fn in PLAN:
    marks[sid]=tm
    c=fn()
    if c: clips.append(c); print(f'  {sid:4s} ok  ({DUR[sid]}s)')
    else: print(f'  {sid:4s} SKIP')
    tm+=DUR[sid]
clips.append(title_card(TITLE))
TOTAL=tm+TITLE
print(f'Runtime {TOTAL:.1f}s')

clips=[c for c in clips if c and os.path.exists(c) and os.path.getsize(c)>20000]
print(f'{len(clips)} valid clips')
if not clips: raise SystemExit('no clips')

lst=os.path.join(WORK,'l.txt')
open(lst,'w').write(''.join(f"file '{c}'\n" for c in clips))
raw=os.path.join(SP,'ep01_v3_raw.mp4')
r=subprocess.run([F,'-y','-f','concat','-safe','0','-i',lst,'-c:v','libx264',
    '-crf','19','-preset','medium','-pix_fmt','yuv420p',raw],capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-400:]); raise SystemExit(1)

# ── AUDIO ────────────────────────────────────────────────────────────────────
print('Voiceover...')
from kokoro_onnx import Kokoro
import soundfile as sf
ko=Kokoro(os.path.join(SP,'kokoro-v1.0.onnx'),os.path.join(SP,'voices-v1.0.bin'))
SR=24000
VO=[(marks['s1']+0.9,"Every city keeps a secret."),
    (marks['s2']+0.7,"Kiran is the only one who can see it."),
    (marks['s3']+0.5,"Every night, at exactly midnight..."),
    (marks['dtr']+0.7,"something begins to open."),
    (marks['s8']+0.4,"A door that was never there before."),
    (marks['s9']+0.3,"And someone waiting on the other side."),
    (marks['s11']+0.7,"The Midnight Market is open.")]
buf=np.zeros(int(SR*(TOTAL+1)),dtype=np.float32)
for st,tx in VO:
    sm,sr=ko.create(tx,voice='am_liam',speed=0.90,lang='en-us')
    if sr!=SR:
        n=int(len(sm)*SR/sr)
        sm=np.interp(np.linspace(0,len(sm)-1,n),np.arange(len(sm)),sm).astype(np.float32)
    i0=int(st*SR); i1=min(i0+len(sm),len(buf)); buf[i0:i1]+=sm[:i1-i0]*0.95
    print(f'  {st:5.1f}s  "{tx}"')
vo=os.path.join(SP,'vo3.wav'); sf.write(vo,np.clip(buf,-1,1),SR)

print('Sound design...')
SR2=44100; ab=np.zeros(int(SR2*(TOTAL+1)),dtype=np.float32)
rng=np.random.default_rng(11)
n=len(ab); wnd=rng.normal(0,1,n).astype(np.float32)
k=900; c=np.cumsum(wnd); wnd=(c[k:]-c[:-k])/k; wnd=np.pad(wnd,(0,n-len(wnd)))
ab+=wnd*0.045
def place(sig,at):
    i0=int(at*SR2); i1=min(i0+len(sig),len(ab)); ab[i0:i1]+=sig[:i1-i0]
def impact(at,amp=0.9):
    d=int(SR2*2.4); t=np.arange(d)/SR2; e=np.exp(-t*2.4)
    s=(np.sin(2*np.pi*44*t)*0.7+np.sin(2*np.pi*66*t)*0.3)*e
    s+=rng.normal(0,1,d)*np.exp(-t*12)*0.22
    place(s.astype(np.float32)*amp,at)
def shimmer(at,amp=0.24):
    d=int(SR2*2.0); t=np.arange(d)/SR2; e=np.exp(-t*1.7); s=np.zeros(d)
    for f0 in (1300,1800,2500,3200,4000,4700):
        s+=np.sin(2*np.pi*f0*t+rng.random()*6)*rng.uniform(.4,1)
    place((s/6*e).astype(np.float32)*amp,at)
def whoosh(at,amp=0.15):
    d=int(SR2*1.5); t=np.arange(d)/SR2
    e=np.sin(np.pi*np.clip(t/(d/SR2),0,1))**2
    place((rng.normal(0,1,d)*e).astype(np.float32)*amp,at)
whoosh(marks['dtr']+0.5); shimmer(marks['dtr']+1.4); shimmer(marks['dtr']+3.2)
impact(marks['der']+0.10,1.0); shimmer(marks['der']+0.5,0.30)
shimmer(marks['dop']+0.3,0.26); shimmer(marks['s9']+0.4,0.24)
whoosh(marks['s11']+0.2); impact(marks['s11']+0.45,0.75)
sfx=os.path.join(SP,'sfx3.wav'); sf.write(sfx,np.clip(ab,-1,1),SR2)

print('Mix...')
final=os.path.join(SP,'ep01_v3_final.mp4')
r=subprocess.run([F,'-y','-i',raw,'-i',vo,'-i',sfx,'-i',MUSIC,'-filter_complex',
  '[1:a]volume=1.0,aresample=48000[vo];[2:a]volume=0.8,aresample=48000[sx];'
  '[3:a]volume=0.19,aresample=48000[mu];'
  '[vo][sx][mu]amix=inputs=3:duration=first:dropout_transition=0,alimiter=limit=0.95[a]',
  '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',final],
  capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-500:]); raise SystemExit(1)
print(f'DONE {final}  {os.path.getsize(final)/1024/1024:.1f}MB')
