#!/usr/bin/env python3
"""
Shot manifest for the five-minute reel.

Each shot is one rendered plate plus a camera move the compositor performs on
it. Shots are grouped by set so the batch renderer builds each set once.

move: (dx, dy, zoom_end) -- pixels of parallax travel over the shot, and the
final zoom factor. Small numbers; parallax multiplies them by disparity.
"""

FPS = 24

SHOTS = [
    # name            set       cam location        look at          lens  secs  move
    ('01_approach',  'forest', (0.5, -16.5, 3.1),  (1.0,  8, 2.6),   35,  22, (14, -4, 1.06)),
    ('02_lanterns',  'forest', (-2.2, -6.0, 2.5),  (2.4,  14, 3.0),  50,  20, (-18, 2, 1.04)),
    ('03_canopy',    'forest', (1.2, 4.0, 1.2),    (0.2,  20, 7.5),  28,  18, (6, -10, 1.09)),
    ('04_deep',      'forest', (-3.0, 16.0, 2.8),  (2.0,  40, 2.4),  40,  21, (12, 0, 1.05)),
    ('05_turn',      'forest', (2.6, 28.0, 3.6),   (-1.5, 48, 2.2),  32,  19, (-15, -3, 1.07)),

    ('06_gate',      'market', (0.0, -18.0, 2.9),  (0.0,  10, 3.0),  34,  23, (0, -6, 1.10)),
    ('07_stalls_l',  'market', (-3.4, -4.0, 2.2),  (3.0,  12, 2.4),  45,  20, (16, 1, 1.04)),
    ('08_stalls_r',  'market', (3.4, 6.0, 2.3),    (-3.0, 22, 2.6),  45,  20, (-16, 1, 1.04)),
    ('09_lane',      'market', (0.0, 14.0, 4.4),   (0.0,  44, 2.0),  38,  22, (0, 5, 1.08)),
    ('10_awnings',   'market', (-1.0, 26.0, 1.5),  (1.5,  40, 4.2),  30,  18, (9, -7, 1.06)),

    ('11_clearing',  'door',   (0.0, -14.0, 3.0),  (0.0,  8,  2.6),  35,  24, (0, -4, 1.12)),
    ('12_door_wide', 'door',   (-6.5, -2.0, 2.4),  (0.0,  8,  2.4),  42,  21, (14, 0, 1.05)),
    ('13_door_close','door',   (0.0, 2.4, 2.3),    (0.0,  8,  2.4),  55,  26, (0, 2, 1.14)),
    ('14_leave',     'door',   (5.0, 1.0, 3.4),    (-2.0, 16, 2.8),  36,  26, (-12, 4, 1.06)),
]

TOTAL_SECONDS = sum(s[5] for s in SHOTS)


def by_set():
    groups = {}
    for s in SHOTS:
        groups.setdefault(s[1], []).append(s)
    return groups


if __name__ == '__main__':
    g = by_set()
    print(f'{len(SHOTS)} shots, {TOTAL_SECONDS}s total '
          f'({TOTAL_SECONDS/60:.2f} min), {TOTAL_SECONDS*FPS} frames')
    for k, v in g.items():
        print(f'  {k:8s} {len(v)} shots  {sum(s[5] for s in v)}s')
