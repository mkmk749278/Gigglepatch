"""Cutout puppet rig for Dora, built from a single canonical plate.

Why one plate: the generated plate pack drifts between images (different tops,
different lanterns, different face styles).  Cutting one plate into parts and
posing it means the design can never drift -- the character becomes a persistent
asset, which is the whole point of ACTIVE_CONTEXT's "consistency is
architectural" finding.

Two details make the difference between a cutout that reads as a puppet and one
that reads as a character:

* **Parts overlap their parent.**  Each part keeps a band of pixels past its cut
  line, and the pivot sits at the joint, so the seam moves almost nowhere when
  the joint rotates.
* **The parent is inpainted behind the part.**  Remove an arm and the torso has
  an arm-shaped hole; swing the arm and the hole shows.  Nearest-colour fill
  pushes the surrounding kurta into the gap, which is what is actually behind an
  arm anyway.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# ---------------------------------------------------------------- materials


def materials(rgba: np.ndarray) -> dict[str, np.ndarray]:
    """Classify plate pixels by what they are made of.

    Geometry alone cannot separate a braid from the sleeve it crosses -- they
    occupy the same box.  Material can: braids are hair and bow, sleeves are
    cloth and skin.
    """
    rgb = rgba[..., :3]
    a = rgba[..., 3] > 0.5
    mx, mn = rgb.max(2), rgb.min(2)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = mx - mn + 1e-6
    h = np.zeros_like(r)
    m = mx == r
    h[m] = ((g - b) / d)[m] % 6
    m = mx == g
    h[m] = (((b - r) / d) + 2)[m]
    m = mx == b
    h[m] = (((r - g) / d) + 4)[m]
    h *= 60.0
    return {
        "alpha": a,
        "sat": s,
        "hair": a & (v < 0.22) & (s < 0.62),
        "skin": a & (h > 8) & (h < 38) & (s > 0.25) & (s < 0.78) & (v > 0.45),
        "cloth": a & (h > 148) & (h < 202) & (s > 0.22),
        "legging": a & (v > 0.68) & (s < 0.20),
        "shoe": a & (((h < 12) | (h > 344)) & (s > 0.42) & (v > 0.28)),
        "gold": a & (h > 26) & (h < 64) & (s > 0.42) & (v > 0.42),
    }


def _disk(r: int) -> np.ndarray:
    y, x = np.mgrid[-r : r + 1, -r : r + 1]
    return (x * x + y * y) <= r * r


def _lerp_curve(knots: list[tuple[float, float]], y: np.ndarray) -> np.ndarray:
    """Piecewise-linear x boundary as a function of y, clamped outside."""
    ys = np.array([k[0] for k in knots], dtype=np.float32)
    xs = np.array([k[1] for k in knots], dtype=np.float32)
    return np.interp(y, ys, xs)


# ---------------------------------------------------------------- part split

# Cut lines measured off the material map of pose_walking.png (491x641).
ARM_NEAR_EDGE = [(215, 278), (260, 258), (312, 243), (340, 215), (390, 178)]
ARM_FAR_EDGE = [(195, 432), (215, 400), (250, 366), (285, 372), (308, 398)]
LEG_SPLIT = [(436, 270), (500, 292), (560, 318), (641, 344)]

PART_ORDER = [
    "back_thigh",
    "back_shin",
    "back_foot",
    "far_arm",
    "right_braid",
    "front_thigh",
    "front_shin",
    "front_foot",
    "torso",
    "head",
    "left_braid",
    "near_arm",
    "lantern",
]

# Leg skeleton in plate coordinates.  A rigid leg swinging from the hip is the
# clearest tell that something is a cutout: the knee never bends and the foot
# never stays put.  Three bones per leg lets the foot be *placed* instead of
# swung, which is what removes skating.
HIP = {"front": (243.0, 438.0), "back": (304.0, 440.0)}
KNEE = {"front": (218.0, 496.0), "back": (340.0, 495.0)}
ANKLE = {"front": (192.0, 552.0), "back": (375.0, 550.0)}
FOOT_CUT = {"front": 540.0, "back": 538.0}

# "backing" is not a body part.  It is the inpainted plate that sits at the very
# back of the stack so that any hole a moving limb opens up shows plausible
# character underneath instead of the sky.  It must be its own layer: baking the
# fill into the torso paints it over the legs, which are drawn behind the torso.
BACKING = "backing"

# Draw order, back to front.  Legs sit behind the kurta hem; the lantern arm and
# its lantern are nearest camera.
Z_ORDER = [
    BACKING,
    "far_arm",
    "back_thigh",
    "back_shin",
    "back_foot",
    "front_thigh",
    "front_shin",
    "front_foot",
    "torso",
    # Both braids drape over the kurta, so they sit in front of the torso; the
    # head goes on last of the three and hides where they root into the skull.
    "right_braid",
    "left_braid",
    "head",
    "near_arm",
    "lantern",
]

# joint -> (pivot x, pivot y, parent)
JOINTS = {
    "torso": (283.0, 452.0, None),
    BACKING: (283.0, 452.0, "torso"),
    "head": (283.0, 210.0, "torso"),
    "left_braid": (222.0, 188.0, "head"),
    "right_braid": (352.0, 244.0, "head"),
    "near_arm": (268.0, 240.0, "torso"),
    "far_arm": (352.0, 246.0, "torso"),
    "lantern": (124.0, 366.0, "near_arm"),
    "front_thigh": (HIP["front"][0], HIP["front"][1], "torso"),
    "front_shin": (KNEE["front"][0], KNEE["front"][1], "front_thigh"),
    "front_foot": (ANKLE["front"][0], ANKLE["front"][1], "front_shin"),
    "back_thigh": (HIP["back"][0], HIP["back"][1], "torso"),
    "back_shin": (KNEE["back"][0], KNEE["back"][1], "back_thigh"),
    "back_foot": (ANKLE["back"][0], ANKLE["back"][1], "back_shin"),
}


def split_masks(rgba: np.ndarray) -> dict[str, np.ndarray]:
    mat = materials(rgba)
    a = mat["alpha"]
    hgt, wid = a.shape
    yy, xx = np.mgrid[0:hgt, 0:wid].astype(np.float32)

    # Braid pixels are "anything dark that is not kurta cloth", not just the
    # strict hair class -- a plait carries specular highlights well above the
    # hair threshold, and dropping them leaves the braid in pieces.
    hairish = (mat["alpha"] & (rgba[..., :3].max(2) < 0.34) & ~mat["cloth"]) | mat["gold"]
    out: dict[str, np.ndarray] = {}
    taken = np.zeros_like(a)

    def claim(name: str, m: np.ndarray, solidify: int = 0, keep_free: bool = False) -> None:
        nonlocal taken
        m = m & a & ~taken
        if keep_free:
            # Bones in a chain deliberately overlap; do not let one consume the
            # pixels the next one also needs.
            out[name] = ndimage.binary_closing(m, np.ones((3, 3)))
            return
        if solidify:
            # A braid read purely by material comes out as separated strands with
            # kurta showing between them; rotate that and it shreds.  Close the
            # gaps so the braid moves as one solid object.
            m = ndimage.binary_closing(m, _disk(solidify))
            m = ndimage.binary_fill_holes(m) & a & ~taken
            # The kurta is embroidered with small gold motifs that read as "gold"
            # too.  Anything this small is a motif, not a braid.
            lab, n = ndimage.label(m)
            if n:
                sizes = ndimage.sum(m, lab, range(1, n + 1))
                m = np.isin(lab, 1 + np.flatnonzero(sizes >= 400))
        else:
            m = ndimage.binary_closing(m, np.ones((3, 3)))
        out[name] = m
        taken = taken | m

    # The lantern hangs clear of everything below the hand.  The right edge has
    # to lean left as it descends, or it clips the front thigh coming down
    # behind it.
    lantern_edge = 205.0 - 0.55 * np.maximum(0.0, yy - 400.0)
    claim("lantern", (yy > 344) & (yy < 545) & (xx < lantern_edge))
    # Above y=140 the dark pixels on this side are the back of the head, not the
    # braid -- the braid only becomes free of the skull below the ear.
    claim("left_braid", hairish & (xx < 205) & (yy > 140) & (yy < 302), solidify=7)
    claim("right_braid", hairish & (xx > 294) & (yy > 208) & (yy < 400), solidify=8)
    claim("head", (yy < 202) | ((yy < 228) & (xx > 248) & (xx < 320)))
    claim("near_arm", (yy > 212) & (yy < 392) & (xx < _lerp_curve(ARM_NEAR_EDGE, yy)))
    claim("far_arm", (yy > 192) & (yy < 312) & (xx > _lerp_curve(ARM_FAR_EDGE, yy)))

    # Legs are whatever is unsaturated below the hem -- white legging, its own
    # shadow, and the shoes.  Testing "not cloth" alone let the kurta's shaded
    # hem join the thigh, and the hem then swung away with the leg.
    leg_mat = mat["legging"] | mat["shoe"] | (a & (mat["sat"] < 0.30) & ~mat["cloth"])
    legs = (yy > 434) & leg_mat
    front = legs & (xx < _lerp_curve(LEG_SPLIT, yy))

    # Each bone keeps a stub past its own joint and its child is drawn on top,
    # so a bend is covered from both sides instead of tearing a wedge open.
    claim("front_thigh", front & (yy < FOOT_CUT["front"]), keep_free=True)
    claim("front_shin", front & (yy >= KNEE["front"][1] - 22), keep_free=True)
    claim("front_foot", front & (yy >= FOOT_CUT["front"] - 14), keep_free=True)
    claim("back_thigh", legs & (yy < FOOT_CUT["back"]), keep_free=True)
    claim("back_shin", legs & (yy >= KNEE["back"][1] - 22), keep_free=True)
    claim("back_foot", legs & (yy >= FOOT_CUT["back"] - 14), keep_free=True)
    taken = taken | legs
    out["leg_region"] = legs
    claim("torso", np.ones_like(a))
    return out


# ---------------------------------------------------------------- inpainting


def grow_fill(rgba: np.ndarray, keep: np.ndarray, within: np.ndarray, reach: int = 60) -> np.ndarray:
    """Extend `rgba` outward from `keep` by nearest-colour, up to `reach` px.

    Used to patch the hole a limb leaves in its parent.  Nearest-colour is crude
    but correct here: behind an arm is more kurta, behind a leg is more legging.

    `within` bounds the fill to the plate's original silhouette.  Without it the
    fill also streaks outward into empty background, and every limb drags a
    smear of colour across the shot the moment it moves.
    """
    dist, idx = ndimage.distance_transform_edt(~keep, return_indices=True)
    filled = rgba[idx[0], idx[1]]
    band = (dist > 0) & (dist <= reach) & within
    out = np.zeros_like(rgba)
    out[keep] = rgba[keep]
    out[band] = filled[band]
    out[..., 3] = np.where(keep | band, np.maximum(out[..., 3], 0.0), 0.0)
    return out


# ---------------------------------------------------------------- parts


class Part:
    """One rigged piece: full-canvas RGBA (premultiplied), a pivot, a parent."""

    def __init__(self, name: str, rgba: np.ndarray, pivot: tuple[float, float], parent: str | None):
        self.name = name
        self.rgba = rgba
        self.pivot = np.array(pivot, dtype=np.float32)
        self.parent = parent


# How far each part reaches past its cut line into its parent.  Thin parts get a
# narrow band -- a wide one on a braid drags half the kurta along with it.
OVERLAP = {
    "head": 18,
    "near_arm": 16,
    "far_arm": 16,
    "front_thigh": 14,
    "front_shin": 16,
    "front_foot": 10,
    "back_thigh": 14,
    "back_shin": 16,
    "back_foot": 10,
    "left_braid": 3,
    "right_braid": 3,
    "lantern": 4,
}


def build(plate_path: str) -> dict[str, Part]:
    img = np.asarray(Image.open(plate_path).convert("RGBA"), dtype=np.float32) / 255.0
    masks = split_masks(img)
    opaque = img[..., 3] > 0.5
    leg_region = masks.pop("leg_region")
    owned = _own_soft_edges(masks, img[..., 3])
    for name in masks:
        if name.endswith(("thigh", "shin", "foot")):
            owned[name] = masks[name]

    parts: dict[str, Part] = {}
    for name in PART_ORDER:
        core = owned[name]
        overlap = OVERLAP.get(name, 0)
        # A leg may only reach into other leg pixels.  Letting a thigh dilate
        # 14px in every direction pulled the kurta hem in with it, and the hem
        # then swung out from under her on every stride.
        limit = leg_region if name.endswith(("thigh", "shin", "foot")) else opaque
        rgba = img.copy()
        if overlap:
            # Keep a band of parent pixels past the cut so the seam has slack.
            grown = ndimage.binary_dilation(core, np.ones((3, 3)), iterations=overlap) & limit
            rgba[..., 3] = rgba[..., 3] * _feather(grown, core, overlap)
        else:
            rgba[..., 3] = rgba[..., 3] * _antialias(core)
        px, py, parent = JOINTS[name]
        parts[name] = Part(name, premultiply(rgba), (px, py), parent)

    fill = grow_fill(img, owned["torso"], within=opaque, reach=80)
    px, py, parent = JOINTS[BACKING]
    parts[BACKING] = Part(BACKING, premultiply(fill), (px, py), parent)
    return parts


def _own_soft_edges(masks: dict[str, np.ndarray], alpha: np.ndarray) -> dict[str, np.ndarray]:
    """Hand every translucent pixel to the part that owns the nearest solid one.

    The part masks are decided on alpha > 0.5, which leaves the lantern's soft
    glow, hair wisps and antialiased rims belonging to nobody -- they vanish from
    every layer.  Nearest-owner assignment puts each of them back on the part
    they visually belong to.
    """
    names = list(masks)
    label = np.zeros(alpha.shape, np.int32)
    for i, n in enumerate(names):
        label[masks[n]] = i + 1
    soft = (alpha > 0.004) & (label == 0)
    if soft.any():
        _, idx = ndimage.distance_transform_edt(label == 0, return_indices=True)
        near = label[idx[0], idx[1]]
        label = np.where(soft, near, label)
    return {n: label == i + 1 for i, n in enumerate(names)}


def _antialias(core: np.ndarray) -> np.ndarray:
    """Half-pixel soft edge on a hard mask, so internal cuts do not stair-step."""
    return np.clip(ndimage.gaussian_filter(core.astype(np.float32), 0.6) * 1.25, 0.0, 1.0)


def _feather(keep: np.ndarray, core: np.ndarray, overlap: int) -> np.ndarray:
    """1 inside the part, ramping to 0 across the overlap band."""
    d = ndimage.distance_transform_edt(~core)
    ramp = np.clip(1.0 - (d - overlap * 0.35) / max(overlap * 0.65, 1.0), 0.0, 1.0)
    return np.where(core, 1.0, ramp * keep)


def premultiply(rgba: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    out[..., :3] *= out[..., 3:4]
    return out


def unpremultiply(rgba: np.ndarray) -> np.ndarray:
    a = np.maximum(rgba[..., 3:4], 1e-5)
    out = rgba.copy()
    out[..., :3] = np.clip(out[..., :3] / a, 0.0, 1.0)
    return out


# ---------------------------------------------------------------- posing


def mat_trs(angle_deg: float, pivot: np.ndarray, offset=(0.0, 0.0), scale=(1.0, 1.0)) -> np.ndarray:
    """3x3 affine: rotate+scale about `pivot`, then translate by `offset`."""
    t = np.radians(angle_deg)
    c, s = np.cos(t), np.sin(t)
    sx, sy = scale
    r = np.array([[c * sx, -s * sy, 0.0], [s * sx, c * sy, 0.0], [0.0, 0.0, 1.0]], np.float32)
    to = np.eye(3, dtype=np.float32)
    to[0, 2], to[1, 2] = -pivot[0], -pivot[1]
    back = np.eye(3, dtype=np.float32)
    back[0, 2], back[1, 2] = pivot[0] + offset[0], pivot[1] + offset[1]
    return back @ r @ to


def world_transforms(parts: dict[str, Part], pose: dict[str, dict]) -> dict[str, np.ndarray]:
    """Compose each part's local transform down the parent chain."""
    world: dict[str, np.ndarray] = {}

    def resolve(name: str) -> np.ndarray:
        if name in world:
            return world[name]
        p = parts[name]
        cfg = pose.get(name, {})
        local = mat_trs(
            cfg.get("angle", 0.0),
            p.pivot,
            cfg.get("offset", (0.0, 0.0)),
            cfg.get("scale", (1.0, 1.0)),
        )
        world[name] = (resolve(p.parent) @ local) if p.parent else local
        return world[name]

    for n in parts:
        resolve(n)
    return world


def render(
    parts: dict[str, Part],
    pose: dict[str, dict],
    canvas: tuple[int, int],
    root: np.ndarray | None = None,
    order: int = 1,
) -> np.ndarray:
    """Composite the posed puppet into an (h, w, 4) premultiplied buffer."""
    h, w = canvas
    out = np.zeros((h, w, 4), np.float32)
    world = world_transforms(parts, pose)
    for name in Z_ORDER:
        p = parts[name]
        m = world[name] if root is None else root @ world[name]
        inv = np.linalg.inv(m)
        layer = _warp(p.rgba, inv, (h, w), order)
        a = layer[..., 3:4]
        out = layer + out * (1.0 - a)
    return out


def _warp(src: np.ndarray, inv: np.ndarray, shape: tuple[int, int], order: int) -> np.ndarray:
    """Apply an inverse affine to a premultiplied RGBA image."""
    mat = np.array([[inv[1, 1], inv[1, 0]], [inv[0, 1], inv[0, 0]]], np.float32)
    off = np.array([inv[1, 2], inv[0, 2]], np.float32)
    chans = [
        ndimage.affine_transform(
            src[..., c], mat, offset=off, output_shape=shape, order=order, mode="constant", cval=0.0
        )
        for c in range(4)
    ]
    out = np.dstack(chans)
    np.clip(out, 0.0, None, out)
    # Premultiplied invariant: colour can never exceed alpha.
    out[..., :3] = np.minimum(out[..., :3], out[..., 3:4])
    return out
