#!/usr/bin/env python3
"""
Narration bed, spoken by Kokoro on CPU.

Lines are timed against the shot list and deliberately sparse -- roughly a
third of the reel has voice on it, so the score and the images carry the rest.
All original text: no existing character, work or person is referenced.
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env

VOICE = 'af_heart'
SPEED = 0.92

# (start seconds, line)
LINES = [
    (2.0,   "Every town has a road that everyone knows."),
    (9.0,   "And one that nobody talks about."),
    (25.0,  "The lanterns are not for the road."),
    (31.5,  "They are for whoever is walking it."),
    (46.0,  "Look up. The trees lean in to listen."),
    (64.0,  "Keep going. The path only opens for someone who keeps going."),
    (85.0,  "And then the trees step aside."),

    (103.0, "The market wakes at midnight."),
    (110.0, "Not because it is hiding. Because that is simply when it is open."),
    (126.0, "Here, a jar of quiet. Bring it home and the whole house softens."),
    (146.0, "Here, a folded map of a place that has not been built yet."),
    (166.0, "Nobody uses money. You trade a story for a story."),
    (188.0, "And the best ones are never the loudest."),

    (206.0, "At the far end of the lane, past the last of the lights,"),
    (213.5, "there is a door."),
    (231.0, "It has no handle, and no lock, and no key."),
    (251.0, "It opens when you stop trying to open it."),
    (262.0, "Some doors are not asking to be solved."),
    (268.0, "They are asking whether you are ready."),
    (280.0, "The market will be here tomorrow."),
    (287.0, "The question is whether you will come back."),
]


def build(sr_out=44100):
    from kokoro_onnx import Kokoro
    import soundfile as sf
    from scipy.signal import resample_poly

    k = Kokoro(env.asset('kokoro-v1.0.onnx'), env.asset('voices-v1.0.bin'))
    total = int(300.0 * sr_out)
    bed = np.zeros(total, np.float32)

    for at, text in LINES:
        s, sr = k.create(text, voice=VOICE, speed=SPEED)
        s = np.asarray(s, np.float32)
        if sr != sr_out:                      # kokoro is 24 kHz, reel is 44.1
            s = resample_poly(s, sr_out, sr).astype(np.float32)
        # short fades stop clicks where lines butt against the music
        f = min(int(0.02 * sr_out), len(s) // 4)
        if f > 0:
            s[:f] *= np.linspace(0, 1, f)
            s[-f:] *= np.linspace(1, 0, f)
        i = int(at * sr_out)
        j = min(total, i + len(s))
        bed[i:j] += s[:j - i]
        print(f'  {at:6.1f}s  {len(s)/sr_out:4.1f}s  {text[:52]}', flush=True)

    peak = float(np.abs(bed).max()) or 1.0
    return (bed / peak * 0.86).astype(np.float32), sr_out


if __name__ == '__main__':
    import soundfile as sf, time
    t0 = time.time()
    bed, sr = build()
    out = os.path.join(env.SP, 'narration.wav')
    sf.write(out, bed, sr)
    spoken = float((np.abs(bed) > 1e-3).mean())
    print(f'\n{out}  {len(bed)/sr:.1f}s in {time.time()-t0:.1f}s  '
          f'voice covers {spoken*100:.0f}% of the reel')
