#!/usr/bin/env python3
"""
Character motion showcase — judge the walk quality.
IK gait + overlapping action + easing + motion blur.
"""
import os, math, subprocess, shutil
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import imageio_ffmpeg
import side_rig2 as S
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != '/' and not _os.path.exists(_os.path.join(_d, 'env.py')):
    _d = _os.path.dirname(_d)
_sys.path.insert(0, _d)
from env import SP
KF=os.path.join(SP,'kf')
W2=os.path.join(SP,'showwork'); shutil.rmtree(W2,ignore_errors=True); os.makedirs(W2)
F=imageio_ffmpeg.get_ffmpeg_exe()
FPS,W,H=30,1280,720
FR='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
FB='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'

SPEED=1.00                          # ~1 stride/sec — a natural walking pace
PPS=S.DIST_PER_CYCLE*SPEED          # rig-units per second of ground travel

def plate(n):
    im=Image.open(os.path.join(KF,f'{n}.jpg')).convert('RGB').resize((W,H),Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(radius=1.4,percent=110,threshold=3))
    return ImageEnhance.Color(im).enhance(1.08)
BG_ST=plate('s1_b'); BG_AL=plate('s5_c')

def cam(img,z,dx=0.0,dy=0.0):
    cw,ch=int(W/z),int(H/z)
    cx=int((W-cw)/2+dx*(W-cw)); cy=int((H-ch)/2+dy*(H-ch))
    cx=max(0,min(W-cw,cx)); cy=max(0,min(H-ch,cy))
    return img.crop((cx,cy,cx+cw,cy+ch)).resize((W,H),Image.LANCZOS)

def shadow(cv,cx,by,rx,ry,a=118):
    sh=Image.new('RGBA',(W,H),(0,0,0,0))
    ImageDraw.Draw(sh).ellipse([cx-rx,by-ry,cx+rx,by+ry],fill=(0,0,0,a))
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))

def label(cv,text,sub=''):
    ol=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ol)
    d.rounded_rectangle([28,26,28+16+d.textlength(text,font=ImageFont.truetype(FB,26))+16,74],
                        radius=10,fill=(0,0,0,120))
    d.text((44,50),text,font=ImageFont.truetype(FB,26),fill=(40,240,215),anchor='lm')
    if sub:
        d.text((30,92),sub,font=ImageFont.truetype(FR,20),fill=(228,228,234),anchor='lm')
    cv.alpha_composite(ol)

# segments: (name, seconds, scale, foot_y, x0, blur_samples, note)
SEG=[('street', 8.0, 0.32, H*0.965, W*1.06, 3, 'IK gait · foot locked to the ground'),
     ('alley',  7.0, 0.46, H*0.955, W*1.06, 4, 'overlapping action · ears and tail lag'),
     ('close',  7.0, 0.62, H*0.965, W*1.02, 5, 'motion blur · 5 sub-frame samples')]
TOTAL=sum(s[1] for s in SEG)

FD=os.path.join(W2,'frames'); os.makedirs(FD)
NF=int(TOTAL*FPS)
print(f'{NF} frames, {TOTAL:.0f}s')

fi=0
for (name,secs,scale,foot_y,x0,samples,note) in SEG:
    n=int(secs*FPS)
    for k in range(n):
        st=k/FPS; p=k/n
        if name=='street':
            bg=cam(BG_ST,1.08,dx=0.70-0.40*p)
        elif name=='alley':
            bg=cam(BG_AL,1.05+0.04*p,dx=0.60-0.34*p)
        else:
            bg=cam(BG_AL,1.14+0.04*p,dx=0.52,dy=0.50)
        cv=bg.convert('RGBA')

        # ground travel always matches stride exactly (no skating)
        x=x0-PPS*scale*st

        def pose_fn(tt):
            po=S.walk(tt,SPEED); po['blink']=S.blink_at(tt); po['mouth']=0.0
            return po
        ch=S.render_blurred(pose_fn,st,scale=scale,samples=samples)
        cw,chh=ch.size; pad=int(S.PAD*scale)
        shadow(cv,int(x),int(foot_y-5),int(118*scale),int(21*scale))
        cv.alpha_composite(ch,dest=(int(x-cw/2),int(foot_y-(chh-pad))))
        label(cv,'CHARACTER MOTION TEST',note)
        cv.convert('RGB').save(os.path.join(FD,f'{fi:05d}.png'))
        fi+=1
        if fi%90==0: print(f'  {fi}/{NF} ({100*fi//NF}%)')

print('Encoding...')
out=os.path.join(SP,'kiran_motion_test.mp4')
subprocess.run([F,'-y','-framerate',str(FPS),'-i',os.path.join(FD,'%05d.png'),
    '-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p',out],capture_output=True)
print(f'DONE {out}  {os.path.getsize(out)/1024/1024:.1f}MB')
