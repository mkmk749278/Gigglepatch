#!/usr/bin/env python3
"""
Compose the reel's 5-minute score.

Structure follows the shot list: the forest is sparse and questioning, the
market warms and picks up pulse, the door section fills out and resolves.
Bars are 8 s -- slow enough that the harmony never competes with narration.
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, music as M

BAR = 8.0
TOTAL = 300.0

# Am7 - Fmaj7 - Cmaj7 - G : floating, unresolved until the last section
PROG = [
    ([('A', 2), ('A', 3), ('C', 4), ('E', 4), ('G', 4)], ('A', 1)),
    ([('F', 2), ('F', 3), ('A', 3), ('C', 4), ('E', 4)], ('F', 1)),
    ([('C', 3), ('C', 4), ('E', 4), ('G', 4), ('B', 4)], ('C', 2)),
    ([('G', 2), ('G', 3), ('B', 3), ('D', 4), ('G', 4)], ('G', 1)),
]


def section(t):
    """Which act a given time belongs to, and how dense it should be."""
    if t < 100:
        return 'forest', 0.35
    if t < 203:
        return 'market', 0.75
    return 'door', 1.0


def build(sr=M.SR, seed=5):
    rng = np.random.default_rng(seed)
    n = int(TOTAL * sr)
    pads = np.zeros(n, np.float32)
    leads = np.zeros(n, np.float32)

    nbars = int(np.ceil(TOTAL / BAR))
    for b in range(nbars):
        at = b * BAR
        chord, root = PROG[b % len(PROG)]
        act, density = section(at)

        freqs = [M.hz(nm, oc) for nm, oc in chord]
        M.mix_into(pads, M.pad(freqs, BAR * 1.15, gain=0.20 + 0.08 * density), at)
        M.mix_into(pads, M.sub(M.hz(*root), BAR * 1.1,
                               gain=0.16 + 0.10 * density), at)

        # arpeggio: sparse in the forest, steady by the door
        steps = {'forest': 4, 'market': 8, 'door': 10}[act]
        for i in range(steps):
            if rng.random() > 0.35 + 0.6 * density:
                continue
            nm, oc = chord[2 + (i % 3)]
            f = M.hz(nm, oc + (1 if rng.random() < 0.25 else 0))
            dur = rng.uniform(1.1, 2.0)
            g = (0.16 + 0.14 * density) * rng.uniform(0.7, 1.0)
            M.mix_into(leads, M.pluck(f, dur, rng=rng),
                       at + i * (BAR / steps) + rng.uniform(-0.05, 0.05), gain=g)

        # a high shimmer to mark each set change
        if abs(at - 100) < BAR or abs(at - 203) < BAR:
            nm, oc = chord[-1]
            M.mix_into(leads, M.pluck(M.hz(nm, oc + 1), 3.2, rng=rng),
                       at, gain=0.22)

    track = M.reverb(pads * 0.9, mix=0.40) + M.reverb(leads, mix=0.30)

    # gentle fades so the reel does not start or stop abruptly
    fi, fo = int(4 * sr), int(7 * sr)
    track[:fi] *= np.linspace(0, 1, fi)
    track[-fo:] *= np.linspace(1, 0, fo)

    peak = float(np.abs(track).max()) or 1.0
    return (track / peak * 0.72).astype(np.float32)


if __name__ == '__main__':
    import soundfile as sf, time
    t0 = time.time()
    tr = build()
    out = os.path.join(env.SP, 'score.wav')
    sf.write(out, tr, M.SR)
    print(f'{out}  {len(tr)/M.SR:.1f}s  built in {time.time()-t0:.1f}s  '
          f'peak {np.abs(tr).max():.3f}')
