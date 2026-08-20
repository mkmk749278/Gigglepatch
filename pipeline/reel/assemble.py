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


def concat_segments(list_p, out_p):
    order = [s[0] for s in SH.SHOTS]
    with open(list_p, 'w') as f:
        for name in order:
            seg = os.path.join(env.SP, 'segments', f'{name}.mp4')
            if not os.path.exists(seg):
                raise FileNotFoundError(f'missing segment {seg}')
            f.write(f"file '{seg}'\n")
    subprocess.run([env.ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat',
                    '-safe', '0', '-i', list_p, '-c', 'copy', out_p], check=True)
    return out_p


def esc(t):
    return t.replace("'", r"\'").replace(':', r'\:')


def finish(video_p, audio_p, out_p):
    # title fades up over the opening shot; sign-off over the last
    dt = (
        f"drawtext=fontfile={FONT}:text='{esc(TITLE)}':"
        f"fontcolor=white@0.92:fontsize=64:x=(w-tw)/2:y=(h-th)/2-30:"
        f"alpha='if(lt(t,2),0,if(lt(t,3.2),(t-2)/1.2,if(lt(t,8),1,"
        f"if(lt(t,9.6),1-(t-8)/1.6,0))))',"
        f"drawtext=fontfile={FONT}:text='{esc(END)}':"
        f"fontcolor=white@0.85:fontsize=40:x=(w-tw)/2:y=(h-th)/2:"
        f"alpha='if(lt(t,292),0,if(lt(t,293.5),(t-292)/1.5,"
        f"if(lt(t,297.5),1,1-(t-297.5)/1.5)))'"
    )
    subprocess.run([
        env.ffmpeg(), '-y', '-loglevel', 'error',
        '-i', video_p, '-i', audio_p,
        '-vf', dt,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest', out_p], check=True)
    return out_p


def main():
    t0 = time.time()
    work = env.SP
    print('concatenating segments ...', flush=True)
    silent = concat_segments(os.path.join(work, 'segments.txt'),
                             os.path.join(work, 'reel_silent.mp4'))

    print('mixing audio ...', flush=True)
    mixed, gmin = duck_mix(os.path.join(work, 'score.wav'),
                           os.path.join(work, 'narration.wav'),
                           os.path.join(work, 'reel_mix.wav'))
    print(f'  music ducks to {gmin:.2f} under narration', flush=True)

    print('encoding final ...', flush=True)
    out = finish(silent, mixed, os.path.join(work, 'midnight_market_reel.mp4'))
    mb = os.path.getsize(out) / 1e6
    print(f'\n{out}\n  {mb:.1f} MB  built in {(time.time()-t0)/60:.1f} min')


if __name__ == '__main__':
    main()
