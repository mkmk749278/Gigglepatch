#!/usr/bin/env python3
"""
Environment + path resolution for the GigglePatch pipeline.

Every script used to hardcode an absolute path into one session's scratchpad.
Those containers are ephemeral, so the moment the session ended the whole
pipeline stopped running. Paths are resolved relative to the repo instead, and
large binaries live in caches that are rebuilt by `fetch_assets.py`.

  REPO    repo root
  SP      working dir for intermediates (override: GIGGLEPATCH_WORK)
  ASSETS  cache for downloaded CC0 assets and models (override: GIGGLEPATCH_ASSETS)
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get('GIGGLEPATCH_WORK', os.path.join(REPO, '.work'))
ASSETS = os.environ.get('GIGGLEPATCH_ASSETS', os.path.join(REPO, '.assets'))
KF = os.path.join(SP, 'kf')

for _d in (SP, ASSETS, KF):
    os.makedirs(_d, exist_ok=True)


def ffmpeg():
    """Static ffmpeg binary. The system one is broken here (libcaca.so.0)."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def asset(name):
    """Absolute path to a cached asset, or raise with how to get it."""
    p = os.path.join(ASSETS, name)
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"missing asset {name!r}\nrun: python3 pipeline/fetch_assets.py")
    return p


def ca_bundle():
    """Outbound HTTPS goes through the agent proxy; requests needs its CA."""
    return os.environ.get('REQUESTS_CA_BUNDLE', '/root/.ccr/ca-bundle.crt')
