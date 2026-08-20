#!/usr/bin/env python3
"""
Rebuild the asset cache from scratch.

The container is ephemeral: every large binary the pipeline needs has to be
re-downloadable, because none of it belongs in git. Run this once per session
before building anything.

    python3 pipeline/fetch_assets.py

3D CC0 packs (Quaternius etc.) are not fetched automatically -- those sites are
JS-driven and their download URLs are content-hashed, so they change. Drop the
zips into .assets/ by hand; everything else here self-installs.
"""
import os, sys, urllib.request, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env

# name -> url. Kokoro is Apache-2.0, CPU-only ONNX inference.
DOWNLOADS = {
    'kokoro-v1.0.onnx':
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/'
        'model-files-v1.0/kokoro-v1.0.onnx',
    'voices-v1.0.bin':
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/'
        'model-files-v1.0/voices-v1.0.bin',
}

PIP = ['numpy', 'pillow', 'imageio', 'imageio-ffmpeg', 'soundfile',
       'onnxruntime', 'kokoro-onnx', 'bpy==4.2.0']


def _hum(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.0f}{u}'
        n /= 1024
    return f'{n:.1f}TB'


def download(name, url):
    dest = os.path.join(env.ASSETS, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f'  have  {name} ({_hum(os.path.getsize(dest))})')
        return
    print(f'  get   {name} ...', flush=True)
    tmp = dest + '.part'
    with urllib.request.urlopen(url) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f)
    os.replace(tmp, dest)
    print(f'  done  {name} ({_hum(os.path.getsize(dest))})')


def main():
    os.environ.setdefault('REQUESTS_CA_BUNDLE', env.ca_bundle())
    print(f'assets -> {env.ASSETS}')
    for name, url in DOWNLOADS.items():
        download(name, url)
    print('\npython deps:')
    print('  pip install ' + ' '.join(PIP))


if __name__ == '__main__':
    main()
