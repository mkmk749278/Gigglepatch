"""Assemble a multi-shot sequence entirely from the puppet pipeline.

A shot is a location, a time of day, one or more rigged characters with their
animations, and a camera move. Shots are rendered in order and concatenated —
no video model anywhere in the chain.

    python3 tools/episode.py out.mp4
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes
from puppet import Animation, Camera, ease, render_shot
from tara_rig import build_chikoo, build_rig, call_out_pause, walk_cycle

FPS = 24
OUT = (1920, 1080)
STAGE = scenes.STAGE


# --------------------------------------------------------------------------
# small animations used by the sequence
# --------------------------------------------------------------------------
def idle(seconds):
    """Breathing and a slow look around. A character standing perfectly still
    reads as a frozen frame, so nothing is ever fully at rest."""
    a = Animation()
    a.track('torso', 'dy', [(0, 0), (1.4, -8), (2.8, 0), (4.2, -8),
                            (5.6, 0), (7.0, -8), (seconds, -4)])
    a.track('torso', 'rot', [(0, -1), (2.6, 1), (5.2, -1), (seconds, 0)])
    a.track('head', 'rot', [(0, 0), (1.8, -7), (3.4, -7), (4.6, 4), (6.2, 0),
                            (seconds, -2)])
    a.track('braid_l', 'rot', [(0, 3), (2.0, 8), (3.8, -3), (5.4, 5), (seconds, 3)])
    a.track('braid_r', 'rot', [(0, -3), (2.1, -8), (3.9, 3), (5.5, -5), (seconds, -3)])
    a.track('arm_r', 'rot', [(0, -14), (seconds, -12)])
    a.track('fore_r', 'rot', [(0, -52), (seconds, -50)])
    a.track('arm_l', 'rot', [(0, 7), (2.4, 10), (5.0, 6), (seconds, 8)])
    a.track('lantern', 'rot', [(0, 66), (seconds, 62)])
    return a


def chikoo_idle(seconds, question_at=None):
    """Twitchy little animal. The tail curls into a question mark on cue."""
    a = Animation()
    a.track('body', 'dy', [(0, 0), (0.7, -5), (1.4, 0), (2.1, -5), (2.8, 0),
                           (3.5, -5), (4.2, 0), (seconds, -3)])
    a.track('head', 'rot', [(0, 0), (0.6, -12), (1.1, 6), (1.9, -8), (2.6, 2),
                            (3.6, -10), (seconds, 0)])
    # Resting angle keeps the tail clear of the body — tucked flat it vanishes
    # behind him and he loses his most recognisable feature.
    if question_at is not None:
        a.track('tail', 'rot', [(0, 26), (question_at - 0.4, 26),
                                (question_at, 64), (question_at + 1.6, 62),
                                (question_at + 2.2, 30), (seconds, 26)])
    else:
        a.track('tail', 'rot', [(0, 26), (1.2, 38), (2.4, 24), (3.6, 36),
                                (seconds, 28)])
    return a


# --------------------------------------------------------------------------
# the sequence
# --------------------------------------------------------------------------
def build_shots():
    tara = build_rig(lit_points=0)
    tara_lit = build_rig(lit_points=1)
    chikoo = build_chikoo()

    # Shot 1 — courtyard, morning. Slow push in.
    cam1 = Camera(STAGE, OUT)
    cam1.track('zoom', [(0, 1.0), (7.0, 1.16)])
    cam1.track('x', [(0, STAGE[0] * 0.50), (7.0, STAGE[0] * 0.52)])
    cam1.track('y', [(0, STAGE[1] * 0.50), (7.0, STAGE[1] * 0.53)])
    shot1 = dict(name='courtyard', dur=7.0,
                 bg=scenes.courtyard(scenes.MORNING, STAGE),
                 rigs=[(tara, idle(7.0))], camera=cam1, shadows=[(tara, 150, 430)])

    # Shot 2 — walking Neem Lane, midday. Static camera, world slides past.
    cam2 = Camera(STAGE, OUT)
    cam2.track('zoom', [(0, 1.06), (9.0, 1.06)])
    cam2.track('y', [(0, STAGE[1] * 0.54), (9.0, STAGE[1] * 0.54)])
    shot2 = dict(name='neem_lane', dur=9.0,
                 bg=scenes.scroller(scenes.neem_lane, scenes.MIDDAY, STAGE, 190),
                 rigs=[(tara, walk_cycle(9.0))], camera=cam2, shadows=[(tara, 140, 430)])

    # Shot 3 — the mango grove. Tara asks; Chikoo does not know either.
    cam3 = Camera(STAGE, OUT)
    cam3.track('zoom', [(0, 1.0), (2.4, 1.26), (10.0, 1.30)])
    cam3.track('x', [(0, STAGE[0] * 0.50), (10.0, STAGE[0] * 0.47)])
    cam3.track('y', [(0, STAGE[1] * 0.50), (10.0, STAGE[1] * 0.55)])
    shot3 = dict(name='mango_grove', dur=10.0,
                 bg=scenes.mango_grove(scenes.MORNING, STAGE),
                 rigs=[(tara, call_out_pause()), (chikoo, chikoo_idle(10.0, 4.6))],
                 camera=cam3, shadows=[(tara, 150, 430), (chikoo, 62, 116)])

    # Shot 4 — the first lantern point lights. Pull back to the wide.
    cam4 = Camera(STAGE, OUT)
    cam4.track('zoom', [(0, 1.30), (5.5, 1.02)])
    cam4.track('y', [(0, STAGE[1] * 0.55), (5.5, STAGE[1] * 0.50)])
    shot4 = dict(name='mango_grove_lit', dur=5.5,
                 bg=scenes.mango_grove(scenes.MORNING, STAGE),
                 rigs=[(tara_lit, idle(5.5)), (chikoo, chikoo_idle(5.5))],
                 camera=cam4, shadows=[(tara_lit, 150, 430), (chikoo, 62, 116)])

    return [shot1, shot2, shot3, shot4]


def place_characters(shot):
    """Position each rig on the stage for this shot."""
    for i, (rig, _) in enumerate(shot['rigs']):
        if 'chikoo' in getattr(rig, 'tag', ''):
            rig.root_pos = (STAGE[0] * 0.655, STAGE[1] * 0.770)
        else:
            rig.root_pos = (STAGE[0] * 0.44, STAGE[1] * 0.52)
    return shot


def render_sequence(out):
    shots = [place_characters(s) for s in build_shots()]
    total = sum(s['dur'] for s in shots)
    print(f'{len(shots)} shots, {total:.1f}s total')

    proc = subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{OUT[0]}x{OUT[1]}', '-r', str(FPS), '-i', 'pipe:0',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
        stdin=subprocess.PIPE)

    for s in shots:
        n = int(s['dur'] * FPS)
        print(f"  {s['name']}: {n} frames", flush=True)
        for i in range(n):
            t = i / FPS
            bg = s['bg'](t) if callable(s['bg']) else s['bg'].copy()
            for rig, radius, foot_drop in s.get('shadows', []):
                x, y = rig.root_pos
                # the shadow belongs under the feet, not under the hips
                scenes.ground_shadow(bg, x, y + foot_drop, radius)
            frame = render_shot(s['rigs'], OUT, t, background=bg, camera=s['camera'])
            proc.stdin.write(frame.convert('RGB').tobytes())
    proc.stdin.close()
    proc.wait()
    print('wrote', out)


if __name__ == '__main__':
    render_sequence(sys.argv[1] if len(sys.argv) > 1 else 'tara_sequence.mp4')
