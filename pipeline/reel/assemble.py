#!/usr/bin/env python3
"""
Concatenate the shot segments, mix the audio, title it, encode the reel.

The music is ducked under the narration rather than mixed flat: a smoothed
envelope of the voice drives a gain reduction on the score, so lines stay
intelligible without having to leave the music quiet throughout.
"""
import os, sys, subprocess, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, shots as SH

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
TITLE = 'The Midnight Market'
END = 'GigglePatch'


def duck_mix(score_p, narr_p, out_p, duck=0.62, attack=0.08, release=0.55):
    import soundfile as sf
    from scipy.signal import lfilter

    score, sr = sf.read(score_p, dtype='float32')
    narr, sr2 = sf.read(narr_p, dtype='float32')
    assert sr == sr2, f'sample rate mismatch {sr} vs {sr2}'
    n = min(len(score), len(narr))
    score, narr = score[:n], narr[:n]

    # smoothed voice envelope -> gain reduction on the music
    e = np.abs(narr)
    a_c = 1.0 - np.exp(-1.0 / (attack * sr))
    r_c = 1.0 - np.exp(-1.0 / (release * sr))
    env_ = lfilter([a_c], [1, -(1 - a_c)], e)
    env_ = lfilter([r_c], [1, -(1 - r_c)], env_)
    env_ = env_ / (env_.max() or 1.0)
    gain = 1.0 - duck * np.clip(env_ * 2.2, 0, 1)

    mix = score * gain.astype(np.float32) + narr * 0.98
    peak = float(np.abs(mix).max()) or 1.0
    if peak > 0.97:
        mix *= 0.97 / peak
    sf.write(out_p, mix, sr)
    return out_p, float(gain.min())


def concat_segments(list_p, out_p, segdir='segments'):
    order = [s[0] for s in SH.SHOTS]
    with open(list_p, 'w') as f:
        for name in order:
            seg = os.path.join(env.SP, segdir, f'{name}.mp4')
            if not os.path.exists(seg):
                raise FileNotFoundError(f'missing segment {seg}')
            f.write(f"file '{seg}'\n")
    subprocess.run([env.ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat',
                    '-safe', '0', '-i', list_p, '-c', 'copy', out_p], check=True)
    return out_p


def title_card(text, size, out_p, w=1280, h=720, dy=0, letterspace=6):
    """
    Render a title to an RGBA PNG.

    The static ffmpeg build here ships without the drawtext filter even though
    freetype is compiled in, so titles are drawn with PIL and composited as an
    overlay instead. It also gives real letter-spacing and a soft shadow,
    which drawtext does not.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    font = ImageFont.truetype(FONT, size)
    glyphs = [(c, font.getbbox(c)) for c in text]
    total = sum(g[1][2] - g[1][0] for g in glyphs) + letterspace * (len(text) - 1)

    card = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    x = (w - total) / 2
    y = (h - size) / 2 + dy
    for c, bb in glyphs:
        d.text((x - bb[0], y), c, font=font, fill=(255, 252, 244, 240))
        x += (bb[2] - bb[0]) + letterspace

    # soft drop shadow so the type holds over a bright frame
    shadow = card.filter(ImageFilter.GaussianBlur(9))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(Image.merge('RGBA', (*[Image.new('L', (w, h), 0)] * 3,
                                             shadow.split()[3].point(lambda v: int(v * 0.75)))))
    out.alpha_composite(card)
    out.save(out_p)
    return out_p


def finish(video_p, audio_p, out_p):
    work = os.path.dirname(out_p)
    t1 = title_card(TITLE, 66, os.path.join(work, '_title.png'), dy=-24)
    t2 = title_card(END, 42, os.path.join(work, '_end.png'))

    fc = (
        "[1:v]format=rgba,fade=in:st=2:d=1.3:alpha=1,"
        "fade=out:st=7.6:d=1.6:alpha=1[t1];"
        "[2:v]format=rgba,fade=in:st=292:d=1.5:alpha=1,"
        "fade=out:st=297.4:d=1.6:alpha=1[t2];"
        "[0:v][t1]overlay=0:0[o1];[o1][t2]overlay=0:0[v]"
    )
    subprocess.run([
        env.ffmpeg(), '-y', '-loglevel', 'error',
        '-i', video_p,
        '-loop', '1', '-i', t1,
        '-loop', '1', '-i', t2,
        '-i', audio_p,
        '-filter_complex', fc,
        '-map', '[v]', '-map', '3:a',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest', out_p], check=True)
    return out_p


def main():
    t0 = time.time()
    work = env.SP
    print('concatenating segments ...', flush=True)
    segdir = os.environ.get('REEL_SEGMENTS', 'segments')
    silent = concat_segments(os.path.join(work, 'segments.txt'),
                             os.path.join(work, 'reel_silent.mp4'), segdir)

    print('mixing audio ...', flush=True)
    mixed, gmin = duck_mix(os.path.join(work, 'score.wav'),
                           os.path.join(work, 'narration.wav'),
                           os.path.join(work, 'reel_mix.wav'))
    print(f'  music ducks to {gmin:.2f} under narration', flush=True)

    print('encoding final ...', flush=True)
    out = finish(silent, mixed, os.path.join(
        work, os.environ.get('REEL_OUT', 'midnight_market_reel.mp4')))
    mb = os.path.getsize(out) / 1e6
    print(f'\n{out}\n  {mb:.1f} MB  built in {(time.time()-t0)/60:.1f} min')


if __name__ == '__main__':
    main()
