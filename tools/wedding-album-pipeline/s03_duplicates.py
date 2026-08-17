"""STAGE 4: DUPLICATE / BURST GROUPING.

Exact duplicates (md5), near-duplicates + burst sequences (perceptual hash
distance combined with capture-time proximity). Nothing is deleted — frames are
grouped and marked so a later stage can pick the strongest frame per group.
Writes analysis/duplicates.json
"""
import hashlib
import json
import sys
from pathlib import Path

import imagehash
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import ANALYSIS

# Thresholds on 16x16 (256-bit) hashes, calibrated against this collection.
# Measured over consecutive pairs shot within 60 s: phash min 10 / p5 40 /
# med 115, where unrelated pairs sit near 128. Frames that are genuinely the
# same shot moments apart land at phash <= ~38, so that is the burst limit.
#
# Note deliberately NOT handled here: long repetitive *sequences* (e.g. the
# blessing line, where 30 frames share one camera setup but each shows a
# different guest) score 90-136 and are correctly not duplicates. Those are
# controlled downstream by per-moment caps and visual curation, not by hashing.
PHASH_SAME = 14        # near duplicate anywhere in the set, regardless of time
PHASH_BURST = 38       # same shot, inside a short time window
AHASH_BURST = 24       # global-layout match (catches reframed repeats)
BURST_SECONDS = 60.0


def hex_to_hash(s, size=16):
    return imagehash.hex_to_hash(s)


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main():
    inv = {r["file"]: r for r in json.loads((ANALYSIS / "photo_inventory.json").read_text())}
    tech = [r for r in json.loads((ANALYSIS / "photo_technical.json").read_text()) if r["ok"]]
    tech.sort(key=lambda r: (inv[r["file"]]["capture_ts"] or 0, r["file"]))
    n = len(tech)
    files = [r["file"] for r in tech]
    ts = np.array([inv[f]["capture_ts"] or 0.0 for f in files])

    # ---------- exact duplicates by content hash
    md5s = {}
    exact = {}
    for f in files:
        h = hashlib.md5(Path(inv[f]["path"]).read_bytes()).hexdigest()
        md5s.setdefault(h, []).append(f)
    for h, g in md5s.items():
        if len(g) > 1:
            exact[h] = g
    print(f"exact duplicate groups (identical bytes): {len(exact)}")

    # ---------- perceptual hash matrices
    ph = np.array([hex_to_hash(r["phash"]).hash.flatten() for r in tech], dtype=bool)
    dh = np.array([hex_to_hash(r["dhash"]).hash.flatten() for r in tech], dtype=bool)

    def dist(mat, i, j):
        return int(np.count_nonzero(mat[i] ^ mat[j]))

    # ---------- candidate pairs.
    # Full 775x775 is cheap in bit-packed form; do it exactly.
    pk_p = np.packbits(ph, axis=1)
    pk_d = np.packbits(dh, axis=1)
    POP = np.unpackbits(np.arange(256, dtype=np.uint8)[:, None], axis=1).sum(1).astype(np.int16)

    def dmat(pk):
        out = np.zeros((n, n), dtype=np.int16)
        for i in range(n):
            out[i] = POP[np.bitwise_xor(pk[i], pk)].sum(1)
        return out

    pk_a = np.packbits(np.array([hex_to_hash(r["ahash"]).hash.flatten() for r in tech],
                                dtype=bool), axis=1)
    Dp, Dd, Da = dmat(pk_p), dmat(pk_d), dmat(pk_a)
    iu = np.triu_indices(n, 1)
    print(f"phash pair distance: min={Dp[iu].min()} p1={np.percentile(Dp[iu],1):.0f} "
          f"med={np.median(Dp[iu]):.0f} max={Dp[iu].max()}")

    dt = np.abs(ts[:, None] - ts[None, :])
    same_day = np.array([[inv[a]["event_day"] == inv[b]["event_day"] for b in files] for a in files])

    near = (Dp <= PHASH_SAME)
    burst = ((Dp <= PHASH_BURST) | (Da <= AHASH_BURST)) & (dt <= BURST_SECONDS) & same_day
    link = np.triu(near | burst, 1)

    dsu = DSU(n)
    for i, j in zip(*np.nonzero(link)):
        dsu.union(int(i), int(j))
    # exact byte duplicates always link
    idx = {f: i for i, f in enumerate(files)}
    for g in exact.values():
        for f in g[1:]:
            dsu.union(idx[g[0]], idx[f])

    groups = {}
    for i, f in enumerate(files):
        groups.setdefault(dsu.find(i), []).append(f)

    clusters = []
    for k, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        members.sort(key=lambda f: inv[f]["capture_ts"] or 0)
        span = (inv[members[-1]]["capture_ts"] or 0) - (inv[members[0]]["capture_ts"] or 0)
        clusters.append({
            "group_id": f"g{len(clusters):03d}",
            "size": len(members),
            "members": members,
            "event_day": inv[members[0]]["event_day"],
            "time_span_s": round(span, 1),
            "kind": ("single" if len(members) == 1 else
                     "exact_duplicate" if any(set(members) <= set(g) for g in exact.values()) else
                     "burst" if span <= BURST_SECONDS * 2 else "near_duplicate"),
        })

    out = {
        "params": {"phash_same": PHASH_SAME, "phash_burst": PHASH_BURST,
                   "burst_seconds": BURST_SECONDS, "hash_size": 16},
        "exact_duplicate_groups": exact,
        "clusters": clusters,
    }
    (ANALYSIS / "duplicates.json").write_text(json.dumps(out, indent=1))

    multi = [c for c in clusters if c["size"] > 1]
    print(f"\ntotal clusters      : {len(clusters)}")
    print(f"singleton frames    : {sum(1 for c in clusters if c['size']==1)}")
    print(f"multi-frame clusters: {len(multi)}")
    print(f"frames inside multi : {sum(c['size'] for c in multi)}")
    print(f"redundant frames    : {sum(c['size']-1 for c in multi)}  (exclusion candidates)")
    from collections import Counter
    print("cluster kinds:", dict(Counter(c["kind"] for c in clusters)))
    print("\nlargest clusters:")
    for c in clusters[:12]:
        if c["size"] > 1:
            print(f"  {c['group_id']} n={c['size']:3d} {c['event_day']} span={c['time_span_s']:7.1f}s "
                  f"{c['kind']:15} {c['members'][0]}..{c['members'][-1]}")


if __name__ == "__main__":
    main()
