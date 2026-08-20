#!/usr/bin/env python3
"""
Render every shot's colour + depth plate.

Grouped by set: building a set costs seconds, rendering costs a minute or more,
so each set is built once and shot from all of its cameras.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import env, sets, shots, plates as P


def main():
    outdir = os.path.join(env.SP, 'plates')
    os.makedirs(outdir, exist_ok=True)
    groups = shots.by_set()
    done, total = 0, len(shots.SHOTS)
    t_start = time.time()

    for set_name, group in groups.items():
        # Only build sets that still owe a render. Blender does not fully free
        # a scene between builds, so rebuilding every set on a partial re-run
        # climbs until the OOM killer takes the process.
        pending = [g for g in group
                   if not os.path.exists(os.path.join(outdir, f'{g[0]}.png'))]
        if not pending:
            print(f'\n=== set {set_name}: all plates present, skipping build ===',
                  flush=True)
            done += len(group)
            continue

        print(f'\n=== building set: {set_name} '
              f'({len(pending)}/{len(group)} plates to render) ===', flush=True)
        t0 = time.time()
        sc = sets.SETS[set_name]()
        print(f'    built in {time.time()-t0:.1f}s', flush=True)

        for name, _s, loc, look, lens, secs, move in pending:
            dt = P.render_plate(sc, name, loc, look, lens)
            done += 1
            el = time.time() - t_start
            eta = el / done * (total - done)
            print(f'    {name:14s} {dt:6.1f}s   [{done}/{total}] '
                  f'eta {eta/60:.1f} min', flush=True)

    print(f'\nALL PLATES DONE in {(time.time()-t_start)/60:.1f} min')


if __name__ == '__main__':
    main()
