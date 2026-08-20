#!/usr/bin/env python3
"""
Prove the pipeline runs end to end in a fresh container.

The container is ephemeral and has no GPU, so the useful question before any
build is "does every stage still work here?". This answers it and prints a
timing budget so episode length can be costed before committing to a render.

    python3 pipeline/fetch_assets.py && python3 pipeline/smoke_test.py
"""
import os, sys, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

FPS, W, H = 24, 960, 540
results = []


def stage(name):
    def deco(fn):
        print(f'\n--- {name} ---')
        t0 = time.time()
        try:
            detail = fn() or ''
            ok = True
        except Exception as e:
            detail, ok = f'{type(e).__name__}: {e}', False
        dt = time.time() - t0
        results.append((name, ok, dt, detail))
        print(f'{"ok " if ok else "FAIL"} {dt:6.2f}s  {detail}')
        return fn
    return deco


@stage('paths')
def _paths():
    return f'work={env.SP} assets={env.ASSETS}'


@stage('ffmpeg')
def _ffmpeg():
    exe = env.ffmpeg()
    v = subprocess.run([exe, '-version'], capture_output=True, text=True)
    return v.stdout.split('\n')[0][:60]


@stage('plate')
def _plate():
    """The rig poses a layered character plate. Synthesize one if the real
    artwork is absent so the mechanics can still be verified."""
    from PIL import Image, ImageDraw
    import numpy as np
    p = os.path.join(env.SP, 'kiran_side.png')
    if os.path.exists(p):
        return f'using existing {os.path.basename(p)}'
    im = Image.new('RGBA', (244, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for box, col in [((8, 0, 205, 302), (232, 168, 124)),
                     ((28, 236, 205, 640), (214, 74, 132)),
                     ((44, 330, 130, 585), (232, 168, 124)),
                     ((44, 588, 170, 752), (240, 128, 48)),
                     ((30, 716, 170, 812), (232, 168, 124)),
                     ((28, 782, 175, 900), (250, 250, 250)),
                     ((138, 575, 244, 712), (196, 92, 48))]:
        d.rounded_rectangle(box, radius=18, fill=col + (255,))
    im.save(p)
    return 'SYNTHETIC placeholder (real artwork missing)'


@stage('rig render')
def _rig():
    sys.path.insert(0, os.path.join(env.REPO, 'pipeline', 'rig'))
    import side_rig2 as R
    frames = []
    t0 = time.time()
    n = FPS  # one second
    for i in range(n):
        frames.append(R.render(R.walk(i / FPS)))
    per = (time.time() - t0) / n
    globals()['_FRAMES'] = frames
    return f'{per*1000:.0f} ms/frame -> {per*FPS:.1f}s compute per video-second'


@stage('encode')
def _encode():
    import numpy as np
    from PIL import Image
    import imageio_ffmpeg
    out = os.path.join(env.SP, 'smoke.mp4')
    wr = imageio_ffmpeg.write_frames(out, (W, H), fps=FPS, quality=7)
    wr.send(None)
    for f in _FRAMES:
        cv = Image.new('RGB', (W, H), (24, 18, 40))
        s = f.copy()
        s.thumbnail((H, H))
        cv.paste(s, (W // 2 - s.width // 2, H - s.height), s)
        wr.send(np.asarray(cv))
    wr.close()
    return f'{os.path.basename(out)} {os.path.getsize(out)//1024}KB'


@stage('tts')
def _tts():
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k = Kokoro(env.asset('kokoro-v1.0.onnx'), env.asset('voices-v1.0.bin'))
    s, sr = k.create('Pipeline check complete.', voice='af_heart')
    sf.write(os.path.join(env.SP, 'smoke.wav'), s, sr)
    return f'{len(s)/sr:.2f}s @ {sr}Hz'


@stage('blender cycles cpu')
def _blender():
    import bpy, addon_utils
    addon_utils.enable('cycles', default_set=True, persistent=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 8
    sc.render.resolution_x, sc.render.resolution_y = 160, 90
    sc.render.filepath = os.path.join(env.SP, 'smoke_bl.png')
    bpy.ops.object.camera_add(location=(0, -5, 1))
    sc.camera = bpy.context.object
    bpy.ops.render.render(write_still=True)
    return f'{sc.render.engine}/{sc.cycles.device}'


print('\n' + '=' * 62)
bad = [r for r in results if not r[1]]
for name, ok, dt, detail in results:
    print(f'{"PASS" if ok else "FAIL"}  {name:22s} {dt:7.2f}s')
print('=' * 62)
print(f'{len(results)-len(bad)}/{len(results)} stages passed')
sys.exit(1 if bad else 0)
