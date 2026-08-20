#!/usr/bin/env python3
"""
Procedural score, synthesised in numpy.

Flow Music sits behind the paid tier and any library track carries licensing
questions, so the score is generated here instead: nothing to clear, and the
structure can be pinned to the shot list exactly.

Plucks use Karplus-Strong -- a short noise burst fed through a decaying delay
line -- which gives a harp/kalimba timbre far more musical than a plain
oscillator, for almost no cost.
"""
import numpy as np
from scipy.signal import lfilter

SR = 44100
A4 = 440.0
NAMES = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4,
         'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}


def hz(name, octave=4):
    return A4 * 2 ** ((NAMES[name] + (octave - 4) * 12) / 12.0)


def _env(n, a=0.01, d=0.1, s=0.7, r=0.3, sr=SR):
    ai, di, ri = int(a * sr), int(d * sr), int(r * sr)
    si = max(0, n - ai - di - ri)
    return np.concatenate([
        np.linspace(0, 1, ai, endpoint=False),
        np.linspace(1, s, di, endpoint=False),
        np.full(si, s),
        np.linspace(s, 0, n - ai - di - si),
    ])[:n]


def pluck(freq, dur, sr=SR, damp=0.996, rng=None):
    """Karplus-Strong string."""
    rng = rng or np.random.default_rng(0)
    n = int(dur * sr)
    L = max(2, int(sr / freq))
    buf = rng.uniform(-1, 1, L)
    out = np.empty(n, np.float32)
    for i in range(n):
        out[i] = buf[i % L]
        nxt = (i + 1) % L
        buf[nxt] = damp * 0.5 * (buf[i % L] + buf[nxt])
    return out * _env(n, a=0.001, d=0.25, s=0.35, r=0.55, sr=sr)


def pad(freqs, dur, sr=SR, detune=0.004, gain=0.22):
    """Warm sustained bed: three detuned saws per note, lightly filtered."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    out = np.zeros(n, np.float32)
    for f in freqs:
        for k, dt in enumerate((-detune, 0.0, detune)):
            ff = f * (1 + dt)
            ph = 2 * np.pi * ff * t
            saw = 2 * (ph / (2 * np.pi) % 1.0) - 1.0
            out += saw * (0.6 if k == 1 else 0.35)
    out /= max(1, len(freqs) * 2)
    # one-pole lowpass: takes the buzz off the saws
    k = 0.055
    y = lfilter([k], [1.0, -(1.0 - k)], out).astype(np.float32)
    return y * _env(n, a=1.2, d=1.0, s=0.85, r=1.8, sr=sr) * gain


def sub(freq, dur, sr=SR, gain=0.3):
    n = int(dur * sr)
    t = np.arange(n) / sr
    return (np.sin(2 * np.pi * freq * t).astype(np.float32)
            * _env(n, a=0.3, d=0.5, s=0.8, r=1.0, sr=sr) * gain)


def reverb(x, sr=SR, mix=0.34, decay=0.72):
    """
    Schroeder reverb: four parallel combs into two series allpasses.

    Written as IIR coefficients so scipy runs them in C -- a per-sample Python
    loop over a five-minute track at 44.1 kHz is 13 M iterations per filter.
    """
    def comb(sig, d_ms, g):
        d = int(sr * d_ms / 1000)
        return lfilter([1.0], [1.0] + [0.0] * (d - 1) + [-g], sig)

    def allpass(sig, d_ms, g):
        d = int(sr * d_ms / 1000)
        b = [-g] + [0.0] * (d - 1) + [1.0]
        a = [1.0] + [0.0] * (d - 1) + [-g]
        return lfilter(b, a, sig)

    wet = np.zeros_like(x, dtype=np.float64)
    for d_ms, g in ((29.7, decay), (37.1, decay * .95),
                    (41.1, decay * .90), (43.7, decay * .85)):
        wet += comb(x, d_ms, g)
    wet /= 4.0
    wet = allpass(wet, 5.0, 0.7)
    wet = allpass(wet, 1.7, 0.7)
    return (x * (1 - mix) + wet.astype(np.float32) * mix).astype(np.float32)


def mix_into(track, seg, at, sr=SR, gain=1.0):
    i = int(at * sr)
    j = min(len(track), i + len(seg))
    if j > i:
        track[i:j] += seg[:j - i] * gain
    return track
