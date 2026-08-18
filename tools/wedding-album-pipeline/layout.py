"""Luxury album page composition (Pillow + numpy).

Each layout is declared as a set of CELLS with known aspect ratios. Photographs
are then assigned to cells by minimising aspect mismatch (optimal assignment,
not first-come order), and the layout itself is chosen by whichever candidate
fits the group's actual orientation mix best. That replaces hand-written
"2 landscapes -> layout X" rules, which inverted badly: a landscape frame forced
into a tall column keeps only a quarter of the frame and slices the scene.

Every page is rendered at trim + bleed. Two-page spreads are rendered as page
pairs with a gutter allowance so nothing critical is swallowed by the binding.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent))
import crop as C
from config import (BLEED_PX, GUTTER_PX, INK, PAGE_H, PAGE_H_BLEED, PAGE_W, PAGE_W_BLEED,
                    PAPER, RULE, SAFE_PX)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

W, H = PAGE_W_BLEED, PAGE_H_BLEED
OUTER = BLEED_PX + 104          # margin for framed layouts
SEAM = 18                       # ivory seam between adjacent photos
_font_cache: dict = {}
PLACEMENTS: list = []


def font(path: str, size: int):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


# ---------------------------------------------------------------- cell specs
# Each entry: list of (box, is_dominant). Aspects are computed from the boxes.


def _cells_full_bleed():
    return [((0, 0, W, H), True)]


def _cells_portrait_showcase():
    """A portrait frame on a landscape page, bleeding off three edges.

    A 2:3 frame shown whole at page height can only cover ~45% of a 4:3 page,
    which leaves over half the sheet blank -- the "small photo in a big frame"
    failure. Instead the panel runs the full bleed height and is cropped to a
    slightly less extreme 0.74 aspect (keeping ~90% of the frame), so it covers
    ~56% of the width and bleeds top, bottom and right. The remaining ivory
    column then reads as a deliberate text margin rather than dead space.
    """
    w = min(int(round(H * 0.74)), int(W * 0.62))
    return [((W - w, 0, w, H), True)]


def _cells_duo_portrait_bleed():
    w = (W - SEAM) // 2
    return [((0, 0, w, H), True), ((w + SEAM, 0, W - w - SEAM, H), False)]


def _cells_duo_portrait_framed():
    h = H - 2 * OUTER
    gap = 76
    w = (W - 2 * OUTER - gap) // 2
    return [((OUTER, OUTER, w, h), True), ((OUTER + w + gap, OUTER, w, h), False)]


def _cells_duo_landscape():
    """Two landscape frames stacked full-bleed.

    Side-by-side does not work for a landscape pair: two 3:2 frames placed in a
    row on a 4:3 page either sit in a narrow band with a third of the sheet
    blank above and below, or have to be cropped to portrait. Stacked full-bleed
    bands fill the page completely and read as a cinematic pair; the crop is
    vertical only, and smart_crop keeps detected faces inside the band.
    """
    h = (H - SEAM) // 2
    return [((0, 0, W, h), True), ((0, h + SEAM, W, H - h - SEAM), False)]


def _cells_duo_dominant():
    bw = int(W * 0.615)
    x = bw + OUTER - BLEED_PX
    w = W - OUTER - x
    h = int((H - 2 * OUTER) * 0.78)
    return [((0, 0, bw, H), True), ((x, (H - h) // 2, w, h), False)]


def _cells_trio_editorial():
    bw = int(W * 0.58)
    x = bw + SEAM
    w = W - x
    h = (H - SEAM) // 2
    return [((0, 0, bw, H), True), ((x, 0, w, h), False),
            ((x, h + SEAM, w, H - h - SEAM), False)]


def _cells_trio_hband():
    """Wide dominant band across the top, two landscape frames beneath."""
    bh = int(H * 0.585)
    w = (W - SEAM) // 2
    return [((0, 0, W, bh), True), ((0, bh + SEAM, w, H - bh - SEAM), False),
            ((w + SEAM, bh + SEAM, W - w - SEAM, H - bh - SEAM), False)]


def _cells_trio_band():
    """Full-height triptych of tall columns - portrait sources only."""
    fr = [0.38, 0.33, 0.29]
    avail = W - 2 * SEAM
    cells, x = [], 0
    for i, f in enumerate(fr):
        w = int(avail * f)
        cells.append(((x, 0, w, H), i == 0))
        x += w + SEAM
    return cells


def _cells_quad_hero():
    bw = int(W * 0.585)
    x = bw + SEAM
    w = W - x
    hs = [(H - 2 * SEAM) // 3] * 3
    hs[2] = H - 2 * SEAM - hs[0] - hs[1]
    cells = [((0, 0, bw, H), True)]
    y = 0
    for h in hs:
        cells.append(((x, y, w, h), False))
        y += h + SEAM
    return cells


def _cells_quad_grid():
    cw = int((W - SEAM) * 0.54)
    cw2 = W - SEAM - cw
    rh = int((H - SEAM) * 0.56)
    rh2 = H - SEAM - rh
    return [((0, 0, cw, rh), True), ((cw + SEAM, 0, cw2, rh), False),
            ((0, rh + SEAM, cw, rh2), False), ((cw + SEAM, rh + SEAM, cw2, rh2), False)]


def _cells_quint_story():
    bw = int(W * 0.56)
    bh = int(H * 0.64)
    x = bw + SEAM
    w = W - x
    h = (bh - SEAM) // 2
    y = bh + SEAM
    hh = H - y
    w1 = int((W - SEAM) * 0.47)
    return [((0, 0, bw, bh), True),
            ((x, 0, w, h), False), ((x, h + SEAM, w, bh - h - SEAM), False),
            ((0, y, w1, hh), False), ((w1 + SEAM, y, W - w1 - SEAM, hh), False)]


def _cells_portrait_showcase_l():
    """Mirror: panel bleeds off the left, ivory text column on the right."""
    w = min(int(round(H * 0.74)), int(W * 0.62))
    return [((0, 0, w, H), True)]


def _mirror(fn):
    """Horizontally mirror a cell spec, giving a visually distinct variant with
    identical aspect ratios (so it costs nothing in fit, only adds rhythm)."""
    def inner():
        return [(((W - (x + w)), y, w, h), dom) for (x, y, w, h), dom in fn()]
    return inner


CELLS = {
    "full_bleed": _cells_full_bleed,
    "portrait_showcase": _cells_portrait_showcase,
    "portrait_showcase_l": _cells_portrait_showcase_l,
    "duo_cinematic": _cells_duo_portrait_bleed,
    "portrait_pair": _cells_duo_portrait_framed,
    "duo_editorial": _cells_duo_landscape,
    "duo_dominant": _cells_duo_dominant,
    "duo_dominant_r": _mirror(_cells_duo_dominant),
    "trio_editorial": _cells_trio_editorial,
    "trio_editorial_r": _mirror(_cells_trio_editorial),
    "trio_hband": _cells_trio_hband,
    "trio_band": _cells_trio_band,
    "quad_hero": _cells_quad_hero,
    "quad_hero_r": _mirror(_cells_quad_hero),
    "quad_grid": _cells_quad_grid,
    "quint_story": _cells_quint_story,
}

# variants that are mirrors of one another: alternating between them is good
# rhythm, but they should not both be treated as "a fresh idea"
MIRROR_FAMILY = {
    "trio_editorial": "trio_editorial_r", "trio_editorial_r": "trio_editorial",
    "duo_dominant": "duo_dominant_r", "duo_dominant_r": "duo_dominant",
    "quad_hero": "quad_hero_r", "quad_hero_r": "quad_hero",
    "portrait_showcase": "portrait_showcase_l", "portrait_showcase_l": "portrait_showcase",
}

CAPACITY = {k: len(v()) for k, v in CELLS.items()}
# layouts whose dominant cell is a genuine hierarchy statement
HIERARCHICAL = {"duo_dominant", "trio_editorial", "trio_hband", "quad_hero", "quint_story"}


def cell_aspects(layout):
    return [box[2] / box[3] for box, _ in CELLS[layout]()]


# ---------------------------------------------------------------- assignment


def assign_cost(item_aspects, layout):
    """Optimal item->cell assignment minimising log-aspect mismatch.

    Returns (mean_cost, order) where order[i] is the item index for cell i.
    """
    cells = cell_aspects(layout)
    n = len(cells)
    if len(item_aspects) != n:
        return float("inf"), None
    cost = np.zeros((n, n), dtype=float)
    for ci, ca in enumerate(cells):
        for ii, ia in enumerate(item_aspects):
            cost[ci, ii] = abs(np.log(ia / ca))
    r, c = linear_sum_assignment(cost)
    order = [int(c[list(r).index(i)]) for i in range(n)]
    return float(cost[r, c].mean()), order


def item_aspect(i):
    """Aspect of an item, from a preloaded image or a declared 'aspect'."""
    if "img" in i:
        return i["img"].shape[1] / i["img"].shape[0]
    return float(i["aspect"])


def choose_layout(items, last_layout=None, allowed=None):
    """Pick the layout whose cells best fit these photographs."""
    n = len(items)
    aspects = [item_aspect(i) for i in items]
    scores = [i.get("final_score", 0.5) for i in items]
    spread = (max(scores) - min(scores)) if n > 1 else 0.0

    best = None
    for lay, cap in CAPACITY.items():
        if cap != n:
            continue
        if allowed and lay not in allowed:
            continue
        cost, order = assign_cost(aspects, lay)
        if order is None:
            continue
        penalty = 0.0
        # reward hierarchy when one frame is clearly stronger, and vice versa
        if lay in HIERARCHICAL:
            penalty += 0.10 if spread < 0.03 else -0.06
            # the dominant cell should hold the strongest frame
            if scores[order[0]] < max(scores) - 1e-9:
                penalty += 0.08
        # Visual rhythm: never repeat the identical layout back to back. Its
        # mirror is only lightly penalised, so a run of same-sized groups
        # alternates sides instead of stamping one grid down the book.
        if lay == last_layout:
            penalty += 0.45
        elif MIRROR_FAMILY.get(last_layout) == lay:
            penalty += 0.04
        cand = (cost + penalty, lay, order)
        if best is None or cand[0] < best[0]:
            best = cand
    if best is None:
        return "quad_grid", list(range(n))
    return best[1], best[2]


# ---------------------------------------------------------------- primitives


def new_page() -> Image.Image:
    return Image.new("RGB", (W, H), PAPER)


def place(canvas: Image.Image, img: np.ndarray, box, faces=None, thirds=True, tag=None):
    x, y, w, h = [int(v) for v in box]
    if w <= 0 or h <= 0:
        return
    src_h, src_w = img.shape[:2]
    cx0, cy0, cx1, cy1 = C.smart_crop_box(img, w / h, faces, thirds)
    fitted = C.fit_cover(img, w, h, faces, thirds)
    canvas.paste(Image.fromarray(fitted), (x, y))
    cw, ch = cx1 - cx0, cy1 - cy0
    PLACEMENTS.append({
        "tag": tag, "box": [x, y, w, h], "source_dims": [src_w, src_h],
        "crop_box": [cx0, cy0, cx1, cy1], "crop_dims": [cw, ch],
        "area_kept": round((cw * ch) / float(src_w * src_h), 4),
        "scale": round(w / max(cw, 1), 4), "upscaled": bool(w > cw),
    })


def tracked_text(draw, xy, text, f, fill, tracking=0, anchor_center=False):
    chars = list(text)
    widths = [draw.textlength(c, font=f) for c in chars]
    total = sum(widths) + tracking * max(0, len(chars) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for c, w_ in zip(chars, widths):
        draw.text((x, y), c, font=f, fill=fill)
        x += w_ + tracking
    return total


def text_width(draw, text, f, tracking=0):
    ws = [draw.textlength(c, font=f) for c in text]
    return sum(ws) + tracking * max(0, len(text) - 1)


def scrim(canvas, side="bottom", frac=0.34, strength=0.62):
    Wc, Hc = canvas.size
    h = int(Hc * frac)
    if side == "bottom":
        g = np.linspace(0, strength, h, dtype=np.float32)[:, None]
        region = (0, Hc - h, Wc, Hc)
    else:
        g = np.linspace(strength, 0, h, dtype=np.float32)[:, None]
        region = (0, 0, Wc, h)
    a = np.repeat(g, Wc, axis=1)
    patch = np.asarray(canvas.crop(region)).astype(np.float32) * (1.0 - a[..., None])
    canvas.paste(Image.fromarray(patch.astype(np.uint8)), (region[0], region[1]))


# ---------------------------------------------------------------- renderers


def render(layout, items, order=None, title=None, subtitle=None, caption=None):
    """Generic renderer: assign items to this layout's cells and place them."""
    cells = CELLS[layout]()
    if order is None:
        _, order = assign_cost([item_aspect(i) for i in items], layout)
        if order is None:
            order = list(range(len(items)))
    page = new_page()
    for (box, _dom), idx in zip(cells, order):
        it = items[idx]
        place(page, it["img"], box, it.get("faces"),
              thirds=(layout != "full_bleed"), tag=it.get("file"))

    d = ImageDraw.Draw(page)
    if layout in ("portrait_showcase", "portrait_showcase_l"):
        box = cells[0][0]
        # Caption sits in whichever margin the photograph is NOT occupying.
        # Compare the panel's CENTRE to the page centre: its left edge alone is
        # misleading for a wide bleeding panel and puts the text off-canvas.
        panel_on_right = (box[0] + box[2] / 2.0) > W / 2.0
        tx = OUTER if panel_on_right else box[0] + box[2] + 110
        maxw = (box[0] - OUTER - 110) if panel_on_right else (W - OUTER - tx)
        d.line([(tx, OUTER), (tx, OUTER + 190)], fill=RULE, width=3)
        if caption:
            f = font(SERIF, 54)
            words, lines, cur = caption.split(), [], ""
            for w_ in words:
                t = (cur + " " + w_).strip()
                if text_width(d, t, f, 4) > maxw and cur:
                    lines.append(cur)
                    cur = w_
                else:
                    cur = t
            lines.append(cur)
            yy = OUTER + 244
            for ln in lines[:5]:
                tracked_text(d, (tx, yy), ln, f, INK, tracking=4)
                yy += 76
            if subtitle:
                tracked_text(d, (tx, yy + 18), subtitle, font(SANS, 34), RULE, tracking=6)
    elif layout == "portrait_pair":
        b0 = cells[0][0]
        cx = b0[0] + b0[2] + 38
        d.line([(cx, b0[1] + b0[3] // 2 - 60), (cx, b0[1] + b0[3] // 2 + 60)],
               fill=RULE, width=3)

    if title and layout in ("full_bleed", "duo_editorial", "trio_hband"):
        scrim(page, "bottom", 0.34, 0.66)
        d = ImageDraw.Draw(page)
        y = H - BLEED_PX - SAFE_PX - 150
        tracked_text(d, (BLEED_PX + SAFE_PX, y), title.upper(), font(SERIF, 104),
                     (255, 251, 244), tracking=16)
        if subtitle:
            tracked_text(d, (BLEED_PX + SAFE_PX + 4, y + 132), subtitle, font(SANS, 40),
                         (238, 226, 206), tracking=8)
    return page


def L_spread(item, chapter=None):
    """One photograph across two facing pages, with a gutter allowance."""
    img, faces = item["img"], item.get("faces") or []
    spread_w = 2 * PAGE_W + 2 * BLEED_PX
    spread_h = H
    x0, y0, x1, y1 = C.smart_crop_box(img, spread_w / spread_h, faces, thirds=False)
    cropped = img[y0:y1, x0:x1]
    ch, cw = cropped.shape[:2]

    if faces:                     # keep faces out of the central gutter band
        sx = cw / max(1, (x1 - x0))
        spine = cw / 2.0
        band = (GUTTER_PX / 2.0) * (cw / spread_w) * 1.6
        local = [((f[0] - x0) * sx + f[2] * sx / 2) for f in faces
                 if x0 <= f[0] and f[0] + f[2] <= x1]
        bad = [c for c in local if abs(c - spine) < band]
        if bad and (x1 - x0) < img.shape[1]:
            worst = min(bad, key=lambda c: abs(c - spine))
            shift = int((band - abs(worst - spine) + 12) / max(sx, 1e-6))
            shift *= 1 if worst < spine else -1
            nx0 = int(np.clip(x0 + shift, 0, img.shape[1] - (x1 - x0)))
            cropped = img[y0:y1, nx0:nx0 + (x1 - x0)]
            ch, cw = cropped.shape[:2]

    if cw < spread_w:
        # No super-resolution model is available here (no GPU, weights not
        # reachable). Lanczos + a light unsharp pass; this does not invent detail.
        full = cv2.resize(cropped, (spread_w, spread_h), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(full, (0, 0), 1.1)
        full = np.clip(full.astype(np.float32) * 1.28 - blur.astype(np.float32) * 0.28,
                       0, 255).astype(np.uint8)
    else:
        full = cv2.resize(cropped, (spread_w, spread_h), interpolation=cv2.INTER_AREA)
    PLACEMENTS.append({
        "tag": item.get("file"), "box": [0, 0, spread_w, spread_h],
        "source_dims": [img.shape[1], img.shape[0]], "crop_dims": [cw, ch],
        "area_kept": round((cw * ch) / float(img.shape[1] * img.shape[0]), 4),
        "scale": round(spread_w / max(cw, 1), 4), "upscaled": bool(cw < spread_w),
    })
    pl, pr = new_page(), new_page()
    pl.paste(Image.fromarray(full[:, :W]), (0, 0))
    pr.paste(Image.fromarray(full[:, spread_w - W:]), (0, 0))
    if chapter:
        scrim(pl, "bottom", 0.30, 0.58)
        d = ImageDraw.Draw(pl)
        tracked_text(d, (BLEED_PX + SAFE_PX, H - BLEED_PX - SAFE_PX - 96),
                     chapter.upper(), font(SERIF, 64), (255, 250, 242), tracking=14)
    return pl, pr


def _title_block(page, title, names, date_line, centre_y=0.635):
    d = ImageDraw.Draw(page)
    cx = W // 2
    y = int(H * centre_y)
    tracked_text(d, (cx, y), title.upper(), font(SERIF, 66), (246, 231, 205),
                 tracking=26, anchor_center=True)
    y += 116
    tracked_text(d, (cx, y), names.upper(), font(SERIF, 128), (255, 253, 248),
                 tracking=18, anchor_center=True)
    y += 190
    d.line([(cx - 300, y), (cx + 300, y)], fill=(214, 186, 140), width=3)
    y += 44
    tracked_text(d, (cx, y), date_line, font(SANS, 44), (236, 224, 204),
                 tracking=14, anchor_center=True)


def L_cover(item, title, names, date_line):
    page = new_page()
    place(page, item["img"], (0, 0, W, H), item.get("faces"), thirds=False,
          tag=item.get("file"))
    scrim(page, "bottom", 0.52, 0.72)
    _title_block(page, title, names, date_line)
    return page


def L_closing(item, line):
    """Closing page. A portrait source uses the same bleeding-panel language as
    the showcase pages (so it fills the sheet rather than floating in ivory),
    with the sign-off set in the remaining column."""
    img = item["img"]
    page = new_page()
    if img.shape[0] > img.shape[1]:
        box = CELLS["portrait_showcase"]()[0][0]
        place(page, img, box, item.get("faces"), tag=item.get("file"))
        d = ImageDraw.Draw(page)
        tx = OUTER
        d.line([(tx, H // 2 - 150), (tx, H // 2 - 40)], fill=RULE, width=3)
        tracked_text(d, (tx, H // 2), line.upper(), font(SERIF, 58), INK, tracking=22)
    else:
        place(page, img, (0, 0, W, H), item.get("faces"), thirds=False, tag=item.get("file"))
        scrim(page, "bottom", 0.42, 0.68)
        d = ImageDraw.Draw(page)
        tracked_text(d, (W // 2, int(H * 0.80)), line.upper(), font(SERIF, 62),
                     (250, 240, 222), tracking=22, anchor_center=True)
    return page
