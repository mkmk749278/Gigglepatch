#!/usr/bin/env python3
"""
Estimate a depth map for each generated plate.

Blender plates came with a true Z pass. Generated images do not, and the
compositor's parallax, fog and depth-of-field are all driven by depth, so it
has to be inferred. Depth-Anything-V2-Small runs on CPU in a few seconds per
image, which is nothing next to the animation pass.

Output matches the Blender convention the compositor already expects:
16-bit PNG, 0 = nearest, 65535 = furthest.
"""
import os, sys, glob, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env

import numpy as np
from PIL import Image, ImageFilter

MODEL = 'depth-anything/Depth-Anything-V2-Small-hf'


def load_model():
    from transformers import pipeline
    return pipeline('depth-estimation', model=MODEL, device=-1)


def estimate(pipe, img_path, smooth=2.0):
    im = Image.open(img_path).convert('RGB')
    out = pipe(im)['predicted_depth']
    d = out.squeeze().cpu().numpy().astype(np.float32)

    # model emits inverse depth (large = near); the compositor wants 0 = near
    d = (d - d.min()) / (float(np.ptp(d)) or 1.0)   # ndarray.ptp() is gone in numpy 2
    d = 1.0 - d

    d = np.asarray(Image.fromarray((d * 255).astype(np.uint8))
                   .resize(im.size, Image.BILINEAR), np.float32) / 255.0
    # a little smoothing: hard edges in the depth map tear under the warp
    d = np.asarray(Image.fromarray((d * 255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(smooth)), np.float32) / 255.0
    return im, d


def main():
    src = os.path.join(env.SP, 'genplates')
    dst = os.path.join(env.SP, 'plates_gen')
    os.makedirs(dst, exist_ok=True)
    files = sorted(f for f in glob.glob(os.path.join(src, '*.jpg'))
                   if not os.path.basename(f).startswith(('v_', 'test_')))
    print(f'{len(files)} plates -> {dst}', flush=True)

    pipe = load_model()
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        t0 = time.time()
        im, d = estimate(pipe, f)

        # trim a small inset: the service stamps a watermark near the edge
        w, h = im.size
        m = int(min(w, h) * 0.035)
        im = im.crop((m, m, w - m, h - m))
        d = d[m:h - m, m:w - m]

        im.save(os.path.join(dst, f'{name}.png'))
        Image.fromarray((np.clip(d, 0, 1) * 65535).astype(np.uint16)).save(
            os.path.join(dst, f'{name}_depth_0001.png'))
        print(f'  {name:14s} {time.time()-t0:5.1f}s  spread {d.min():.2f}-{d.max():.2f}',
              flush=True)


if __name__ == '__main__':
    main()
