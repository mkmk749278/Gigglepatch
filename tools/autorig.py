"""Cut a single character image into puppet parts, automatically.

There is no code behind a generated character image — it is a flat raster, with
no bones, no layers and no geometry to extract. But the inverse works: given one
image of a character standing in a known pose, the silhouette can be analysed
and cut into limbs, and those limbs rigged.

That turns "generate twelve separate parts and hope they match" into "generate
one good picture", which is a far easier thing to art-direct.

How it works
    Scan the silhouette row by row. Where a row contains three separate runs of
    opaque pixels, the outer two are arms and the middle is the torso. Where the
    single run narrows sharply near the top, that is the neck. Where one run
    splits into two near the bottom, those are the legs. Everything else follows
    from proportion.

Requires an A-POSE reference: standing, front on, arms held clearly away from
the body, legs slightly apart, on a transparent background. That pose exists
precisely so limbs can be told apart — with arms flat against the sides there is
no seam to cut along, and no amount of cleverness invents one.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def chroma_key(arr, thresh=60):
    """Magenta-key mask: True where the pixel is background.

    Flat-colour distance keying is not enough in practice. Generated backgrounds
    come back as a *gradient* — measured 205 to 241 across one frame — which
    blows past any tolerance tight enough to keep the character's dark hair.

    Magenta is red and blue high with green low, and no part of this cast is
    magenta, so `min(R, B) - G` separates them with enormous margin: background
    sits near 150, while teal, skin, gold, red shoes, black hair and white
    leggings all land at or below zero. The measure is a ratio between channels,
    so a brightness gradient moves it barely at all — and the soft drop shadow
    under the feet is still magenta, so it keys out with everything else.
    """
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return (np.minimum(r, b) - g) > thresh


def largest_blob(mask):
    """Keep only the biggest connected region — drops watermarks and specks."""
    m = mask.astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 2:
        return mask
    keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == keep


def despill(arr, alpha, thresh=60):
    """Pull magenta fringe out of the edge pixels the key left behind."""
    out = arr.copy()
    edge = (alpha > 0) & (alpha < 255)
    if not edge.any():
        edge = alpha > 0
    r, g, b = [out[..., i].astype(np.int16) for i in range(3)]
    spill = np.minimum(r, b) - g
    hit = edge & (spill > 0)
    cap = g + np.maximum(spill - thresh, 0)
    for i, ch in ((0, r), (2, b)):
        out[..., i] = np.where(hit, np.minimum(ch, np.maximum(cap, 0)), ch).clip(0, 255)
    return out


def load_rgba(path, bg_tolerance=26, key=None, keep_largest=True):
    """Load an image, removing the background if it is not already cut out.

    `key` forces a route: 'chroma' for a magenta screen, 'flat' for a solid
    colour. Left as None it picks chroma whenever the corners actually are
    magenta, which is what our own prompts ask the model for.

    `keep_largest` discards everything but the biggest connected region, which
    removes the model's corner watermark from a single-character image. Turn it
    off for a strip of separate objects — mouth shapes, lantern stages — or it
    will keep exactly one of them.
    """
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im)[..., 3]
    if a.min() < 250:                      # already has transparency
        return im
    arr = np.asarray(im).astype(np.int16)

    corners = np.stack([arr[0, 0, :3], arr[0, -1, :3], arr[-1, 0, :3], arr[-1, -1, :3]])
    is_magenta = np.median(np.minimum(corners[:, 0], corners[:, 2]) - corners[:, 1]) > 60

    if key == 'chroma' or (key is None and is_magenta):
        fg = ~chroma_key(arr)
        if keep_largest:
            fg = largest_blob(fg)
        alpha = np.where(fg, 255, 0).astype(np.uint8)
        # one-pixel erode-then-feather: the key leaves a rim of blended
        # background on every edge, and it is magenta
        alpha = cv2.erode(alpha, np.ones((3, 3), np.uint8), iterations=1)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        out = despill(arr.astype(np.uint8), alpha)
    else:
        bg = np.median(corners, axis=0)
        dist = np.abs(arr[..., :3] - bg).sum(axis=-1)
        alpha = np.where(dist < bg_tolerance * 3, 0, 255).astype(np.uint8)
        out = arr.astype(np.uint8)

    out = out.copy()
    out[..., 3] = alpha
    return Image.fromarray(out.astype(np.uint8))


def runs(row, min_len=3):
    """Contiguous opaque spans in one scanline, as (start, end) pairs."""
    idx = np.flatnonzero(row)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks + 1]])
    ends = np.concatenate([idx[breaks], [idx[-1]]])
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e - s >= min_len]


def analyse(im):
    """Find the landmarks a rig needs by tracking the body's central column.

    Naive rules fail on this shape. Taking the narrowest row as the neck picks
    the top of the head, because the crown is a single narrow run. Taking the
    first row with three runs as the shoulders fires at chin level, because
    braids either side of the head are also three runs. Both mistakes come from
    looking at the silhouette as a whole rather than following the body down.
    """
    a = (np.asarray(im)[..., 3] > 24)
    h, w = a.shape
    ys = np.flatnonzero(a.any(axis=1))
    if ys.size == 0:
        raise ValueError('image is empty')
    top, bottom = int(ys[0]), int(ys[-1])
    span = bottom - top

    rows = [runs(a[y]) for y in range(h)]
    cx = int(np.median(np.flatnonzero(a.any(axis=0))))

    def central(y):
        """The run this row contributes to the body, not to an outflung limb."""
        rs = rows[y]
        if not rs:
            return None
        hit = [r for r in rs if r[0] - 6 <= cx <= r[1] + 6]
        return max(hit or rs, key=lambda r: r[1] - r[0])

    cw = np.zeros(h)
    for y in range(top, bottom + 1):
        r = central(y)
        cw[y] = (r[1] - r[0]) if r else 0

    # head: widest point of the skull, then the narrowest row beneath it
    head_hi = top + int(span * 0.06)
    head_lo = top + int(span * 0.34)
    head_max = head_hi + int(np.argmax(cw[head_hi:head_lo]))
    neck_lo = min(top + int(span * 0.55), bottom)
    neck_y = head_max + int(np.argmin(cw[head_max:neck_lo]))

    # shoulders: the first clear widening below the neck
    neck_w = max(cw[neck_y], 1)
    shoulder_y = neck_y + int(span * 0.04)
    for y in range(neck_y + 2, neck_lo):
        if cw[y] > neck_w * 1.30:
            shoulder_y = y
            break

    # Torso columns must be measured only on rows where the arms have visibly
    # separated from the body. Sampling just below the shoulder catches the rows
    # where the upper arms still overlap the torso, and returns a span reaching
    # armpit to armpit — which then drags the hip line up with it.
    three = [y for y in range(shoulder_y, min(top + int(span * 0.74), bottom))
             if len(rows[y]) >= 3]
    mids = []
    for y in three:
        m = [r for r in rows[y] if r[0] - 6 <= cx <= r[1] + 6]
        if m:
            mids.append(m[0])
    if len(mids) >= 3:
        torso_x = (int(np.median([m[0] for m in mids])),
                   int(np.median([m[1] for m in mids])))
    else:
        tr = central(min(shoulder_y + int(span * 0.30), bottom))
        torso_x = tr if tr else (cx - span // 10, cx + span // 10)

    # hips: where the central column splits into two legs
    hip_y = top + int(span * 0.58)
    for y in range(top + int(span * 0.45), bottom):
        inside = [r for r in rows[y]
                  if torso_x[0] - 10 <= (r[0] + r[1]) / 2 <= torso_x[1] + 10]
        if len(inside) >= 2:
            hip_y = y
            break

    # Refine the torso columns now that the hip is known. The first pass takes a
    # median over every arms-clear row, which lands between the waist and the
    # hem and so reads narrower than the garment — measured 138px against a
    # 185px kurta, which would leave a strip of tunic attached to each arm. The
    # band just above the hip is where the tunic is widest and the arms are
    # furthest away, so measure there and take the widest reading.
    # A-pose arms end well above the hip, so this band usually holds a single
    # run — and that run is the whole garment. Requiring three runs here finds
    # nothing; requiring one is what actually measures the tunic.
    lo = max(hip_y - int(span * 0.14), shoulder_y + int(span * 0.06))
    hi = max(hip_y - int(span * 0.02), lo + 1)
    wide = []
    for y in range(lo, min(hi, bottom)):
        inner = [r for r in rows[y] if r[0] - 6 <= cx <= r[1] + 6]
        if inner and (len(rows[y]) == 1 or len(rows[y]) >= 3):
            wide.append(max(inner, key=lambda r: r[1] - r[0]))
    if wide:
        torso_x = (min(r[0] for r in wide), max(r[1] for r in wide))

    return dict(top=top, bottom=bottom, neck_y=neck_y, shoulder_y=shoulder_y,
                hip_y=hip_y, torso_x=tuple(torso_x), rows=rows, w=w, h=h, cx=cx)


def cut(im, box, feather=0):
    """Extract a region of the source image.

    Feathering defaults off. It was meant to stop joints showing a hard seam,
    but it softens the *crop boundary* too — and where two parts butt together,
    torso against arm, two semi-transparent edges meet and the background shows
    through as a light line down the join. The chroma key already leaves a soft
    edge on the true silhouette, which is the only place softness is wanted.
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    part = im.crop((x0, y0, x1, y1))
    if feather:
        a = part.split()[3].filter(ImageFilter.GaussianBlur(feather * 0.5))
        part.putalpha(a)
    return part


def split_parts(path, out_dir):
    """Cut an A-pose reference into rig parts and record their pivots."""
    im = load_rgba(path)
    m = analyse(im)
    os.makedirs(out_dir, exist_ok=True)
    h_total = m['bottom'] - m['top']
    tx0, tx1 = m['torso_x']
    parts = {}

    def save(name, box, pivot_rel):
        p = cut(im, box)
        p.save(os.path.join(out_dir, f'{name}.png'))
        parts[name] = dict(file=f'{name}.png', size=p.size,
                           pivot=[round(p.width * pivot_rel[0]),
                                  round(p.height * pivot_rel[1])],
                           box=[int(v) for v in box])

    # head: top of the silhouette down to just past the neck
    save('head', (max(tx0 - h_total * 0.10, 0), m['top'],
                  min(tx1 + h_total * 0.10, m['w']), m['neck_y'] + h_total * 0.03),
         (0.5, 0.94))

    # torso: neck to hips, arm-free columns only
    save('torso', (tx0, m['neck_y'] - h_total * 0.01, tx1, m['hip_y'] + h_total * 0.02),
         (0.5, 0.06))

    # Arms: everything outside the torso columns, between shoulder and hips.
    # The box overlaps the torso by a few pixels so the shoulder does not open a
    # gap when the arm rotates — but that overlap is a strip of tunic running
    # the full height of the crop, and it would swing with the arm as a teal
    # shard. Keep it at the shoulder, erase it below.
    overlap = 4
    keep_to = m['shoulder_y'] + h_total * 0.16
    for side, box in (('arm_l', (0, m['shoulder_y'] - h_total * 0.03, tx0 + overlap,
                                 m['hip_y'] + h_total * 0.08)),
                      ('arm_r', (tx1 - overlap, m['shoulder_y'] - h_total * 0.03,
                                 m['w'], m['hip_y'] + h_total * 0.08))):
        save(side, box, (0.85 if side == 'arm_l' else 0.15, 0.08))
        f = os.path.join(out_dir, f'{side}.png')
        p = Image.open(f)
        a = np.asarray(p).copy()
        cut_row = int(keep_to - box[1])
        strip = slice(-overlap, None) if side == 'arm_l' else slice(0, overlap)
        a[max(cut_row, 0):, strip, 3] = 0
        Image.fromarray(a).save(f)

    # legs: split the lower half down the centre of the torso
    mid_x = (tx0 + tx1) / 2
    save('leg_l', (tx0 - h_total * 0.02, m['hip_y'] - h_total * 0.01,
                   mid_x + 4, m['bottom'] + 2), (0.62, 0.04))
    save('leg_r', (mid_x - 4, m['hip_y'] - h_total * 0.01,
                   tx1 + h_total * 0.02, m['bottom'] + 2), (0.38, 0.04))

    meta = dict(source=os.path.basename(path), landmarks={
        k: (v if not isinstance(v, tuple) else list(v))
        for k, v in m.items() if k != 'rows'}, parts=parts)
    json.dump(meta, open(os.path.join(out_dir, 'rig.json'), 'w'), indent=1)
    return meta


def annotate(path, out):
    """Draw the detected landmarks over the source, so a bad cut is obvious."""
    im = load_rgba(path).convert('RGBA')
    m = analyse(im)
    d = ImageDraw.Draw(im)
    for y, col, label in ((m['top'], (0, 160, 255), 'top'),
                          (m['neck_y'], (255, 40, 40), 'neck'),
                          (m['shoulder_y'], (255, 160, 0), 'shoulder'),
                          (m['hip_y'], (0, 200, 90), 'hip'),
                          (m['bottom'], (0, 160, 255), 'bottom')):
        d.line([(0, y), (m['w'], y)], fill=col + (220,), width=3)
        d.text((8, max(y - 20, 2)), label, fill=col + (255,))
    for x in m['torso_x']:
        d.line([(x, m['neck_y']), (x, m['hip_y'])], fill=(220, 0, 220, 200), width=3)
    im.convert('RGB').save(out, quality=94)
    return m


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else 'parts_out'
    meta = split_parts(src, dst)
    print(f"cut {len(meta['parts'])} parts into {dst}/")
    for name, p in meta['parts'].items():
        print(f"  {name:8s} {p['size'][0]:4d}x{p['size'][1]:<4d} pivot {p['pivot']}")
