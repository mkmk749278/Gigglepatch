"""Motion for the Dora rig.

The things that separate "the drawing is moving" from "the character is walking"
are all in here, and they are all cheap:

* **Hip height is derived, not invented.**  With a straight cutout leg the hip
  rides highest at mid-stance, by exactly L*(1-cos t).  Bobbing the body by that
  amount keeps the planted foot on the ground instead of sliding through it, and
  it produces the real two-per-cycle bounce for free.
* **Nothing arrives at the same time.**  Chest, head, braids and lantern each lag
  the hips by a different amount, so the body reads as connected mass rather than
  one rigid stamp.
* **Loose things are simulated, not keyframed.**  Braids and the lantern are
  damped springs driven by their parent, so they overshoot and settle the way
  hanging objects do.
"""

from __future__ import annotations

import math

import numpy as np

TAU = math.pi * 2.0

# Gait, in plate pixels.  HALF_STRIDE is how far the ankle travels either side of
# the hip; STANCE is the fraction of the cycle a foot spends on the ground (>0.5,
# so there is a double-support overlap, as in a real walk rather than a run).
HALF_STRIDE = 45.0
STANCE = 0.62
FOOT_LIFT = 26.0
ANKLE_GROUND = 551.0
HIP_Y = 439.0
REACH = 0.99  # never let a stance leg lock dead straight, but do not crouch


def ease(t: np.ndarray | float) -> np.ndarray | float:
    """Smoothstep -- used anywhere a value would otherwise start or stop hard."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def spring(drive: np.ndarray, freq: float, damp: float, dt: float, scale: float = 1.0) -> np.ndarray:
    """Damped second-order follow of `drive`, evaluated over the whole take.

    Used for braids and the lantern.  The output trails the input, overshoots on
    a direction change and rings down -- which is the entire visual signature of
    hanging hair and a swinging lamp.

    Integrated with sub-steps.  Explicit integration of a spring is only stable
    while w*dt stays well under 2, and a take sampled at a low rate (a 10-frame
    gait test, say) silently goes unstable and throws the braid off the screen.
    Sub-stepping makes the result depend on the spring, not the sample rate.
    """
    w = TAU * freq
    sub = max(1, int(np.ceil(w * dt / 0.2)))
    h = dt / sub
    x = np.zeros_like(drive)
    v = 0.0
    pos = float(drive[0])
    for i in range(len(drive)):
        prev = float(drive[i - 1]) if i else float(drive[0])
        for k in range(sub):
            target = prev + (float(drive[i]) - prev) * ((k + 1) / sub)
            acc = w * w * (target - pos) - 2.0 * damp * w * v
            v += acc * h
            pos += v * h
        x[i] = pos
    return (x - drive) * scale


def lag(curve: np.ndarray, frames: float) -> np.ndarray:
    """Delay a curve by a fractional number of frames, wrapping at the ends."""
    idx = np.arange(len(curve), dtype=np.float32) - frames
    return np.interp(idx, np.arange(len(curve)), curve, period=len(curve))


class WalkTake:
    """Every joint curve for a walking shot, sampled per frame."""

    def __init__(self, frames: int, fps: int = 24, cycle: float = 1.05, breath: float = 0.4):
        self.cycle = cycle
        self.frames = frames
        self.fps = fps
        dt = 1.0 / fps
        t = np.arange(frames, dtype=np.float32) / fps
        # phase 0 == the plate pose: near leg forward, far leg trailing.
        ph = (t / cycle) * TAU
        self.phase = ph

        swing = np.cos(ph)
        # The legs are solved, not swung: feet are placed on a stance/swing plan
        # and the joint angles come back from IK.
        self.gait = solve_walk((t / cycle) % 1.0)
        self.hip_y = self.gait["hip_y"]

        # Weight shift comes back from the solve so the IK and the torso agree.
        self.hip_x = self.gait["hip_x"]
        self.torso_rot = -1.1 * np.sin(ph) + 0.6 * np.sin(ph * 2.0)

        # Arms counter-swing the legs, and lag the hips slightly.
        self.near_arm = lag(-9.0 * swing - 2.0, 1.5)
        self.far_arm = lag(9.0 * swing, 1.5)

        # Breathing rides on top of everything, on its own slow clock.
        br = np.sin(TAU * breath * t)
        self.breath = 1.0 + 0.012 * br
        self.head_rot = lag(-1.6 * np.sin(ph) + 0.8 * br, 3.5)

        # Loose objects: driven by where their anchor actually goes.  Kept small
        # -- a braid that swings far enough to leave the head reads as a separate
        # object flying alongside her, which is exactly the cutout tell to avoid.
        head_drive = self.head_rot + self.torso_rot
        self.left_braid = spring(head_drive - self.hip_y * 0.30, 2.3, 0.42, dt, scale=1.0)
        self.right_braid = spring(head_drive - self.hip_y * 0.26, 2.6, 0.45, dt, scale=0.85)
        self.lantern = spring(self.near_arm, 1.5, 0.30, dt, scale=1.4)


        self.blink = blink_track(frames, fps)

    def pose(self, i: int) -> dict[str, dict]:
        return {
            "torso": {
                "angle": float(self.torso_rot[i]),
                "offset": (float(self.hip_x[i]), float(self.hip_y[i])),
                "scale": (1.0, float(self.breath[i])),
            },
            "head": {"angle": float(self.head_rot[i])},
            "left_braid": {"angle": float(self.left_braid[i])},
            "right_braid": {"angle": float(self.right_braid[i])},
            "near_arm": {"angle": float(self.near_arm[i])},
            "far_arm": {"angle": float(self.far_arm[i])},
            "lantern": {"angle": float(self.lantern[i])},
            "front_thigh": {"angle": float(self.gait["front_thigh"][i])},
            "front_shin": {"angle": float(self.gait["front_shin"][i])},
            "front_foot": {"angle": float(self.gait["front_foot"][i])},
            "back_thigh": {"angle": float(self.gait["back_thigh"][i])},
            "back_shin": {"angle": float(self.gait["back_shin"][i])},
            "back_foot": {"angle": float(self.gait["back_foot"][i])},
        }


def solve_walk(p: np.ndarray) -> dict[str, np.ndarray]:
    """Place both feet, drop the pelvis to suit, then IK every joint.

    Returns part rotations in degrees, already expressed relative to the plate's
    own rest pose, plus the hip offset in plate pixels.
    """
    from . import rig

    legs = {"front": 0.0, "back": 0.5}
    ankle = {}
    for name, offset in legs.items():
        ax, ay, stance = ankle_path(p + offset)
        hx, hy = rig.HIP[name]
        ankle[name] = (hx + ax, ay, stance, p + offset)

    # The pelvis can only ride as high as the most extended stance leg permits.
    hip_y = np.full_like(p, -1e9)
    for name, (ax, ay, stance, _) in ankle.items():
        hx, _hy = rig.HIP[name]
        l1, l2 = _bones(name)
        reach = (l1 + l2) * REACH
        dx = np.clip(np.abs(ax - hx), 0.0, reach - 1.0)
        need = ay - np.sqrt(reach * reach - dx * dx)
        hip_y = np.where(stance, np.maximum(hip_y, need), hip_y)
    hip_y = np.where(hip_y < -1e8, HIP_Y, hip_y)

    dy = hip_y - HIP_Y
    dx = pelvis_sway(p)
    out: dict[str, np.ndarray] = {"hip_y": dy, "hip_x": dx}
    for name, (ax, ay, stance, ph) in ankle.items():
        hx, hy = rig.HIP[name]
        l1, l2 = _bones(name)
        rest_t, rest_s = _rest_dirs(name)
        thigh = np.zeros_like(p)
        shin = np.zeros_like(p)
        # Solve in the torso's own frame.  The legs hang off the torso, so the
        # pelvis offset is already applied to their pivots by the hierarchy --
        # solving against a world-space hip would apply it a second time and
        # fold the legs up under her.
        for i in range(len(p)):
            td, sd = solve_leg(
                np.array([hx, hy]), np.array([ax[i] - dx[i], ay[i] - dy[i]]), l1, l2
            )
            thigh[i], shin[i] = td, sd
        t_deg = np.degrees(thigh - rest_t)
        s_deg = np.degrees(shin - rest_s) - t_deg
        out[f"{name}_thigh"] = t_deg
        out[f"{name}_shin"] = s_deg
        # Keep the shoe near level with the ground rather than aligned to the
        # shin, but only partly -- fully counter-rotating a plate foot that was
        # drawn mid-toe-off swings it through 60 degrees and it reads as broken.
        correct = np.clip(-(t_deg + s_deg) * 0.7, -22.0, 22.0)
        out[f"{name}_foot"] = foot_roll(ph) + correct
    return out


def pelvis_sway(p: np.ndarray) -> np.ndarray:
    """Small lateral shift of the pelvis over the supporting leg."""
    return 1.6 * np.sin(TAU * 2.0 * p)


def _bones(name: str) -> tuple[float, float]:
    from . import rig

    hip = np.array(rig.HIP[name])
    knee = np.array(rig.KNEE[name])
    ankle = np.array(rig.ANKLE[name])
    return float(np.hypot(*(knee - hip))), float(np.hypot(*(ankle - knee)))


def _rest_dirs(name: str) -> tuple[float, float]:
    from . import rig

    hip = np.array(rig.HIP[name])
    knee = np.array(rig.KNEE[name])
    ankle = np.array(rig.ANKLE[name])
    return (
        float(np.arctan2(*(knee - hip)[::-1])),
        float(np.arctan2(*(ankle - knee)[::-1])),
    )


def ground_speed(cycle: float) -> float:
    """Plate px/s of ground travel that exactly matches the stance plan."""
    return (2.0 * HALF_STRIDE) / (STANCE * cycle)


def ankle_path(p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Where one ankle is, as a function of gait phase p in [0,1).

    Stance is the important half.  The foot is on the ground and the ground is
    moving under a camera that tracks her, so relative to the hips the ankle
    travels *linearly* from front to back.  A cosine here is what makes cutout
    walks skate: the foot would drift fast at mid-stance and stall at the ends
    while the ground scrolls at a constant rate.
    """
    p = p % 1.0
    stance = p < STANCE
    u_st = np.clip(p / STANCE, 0.0, 1.0)
    u_sw = np.clip((p - STANCE) / (1.0 - STANCE), 0.0, 1.0)

    # She travels screen-left, so "forward" is -x: a foot lands ahead of the hip
    # at -HALF_STRIDE and is dragged back to +HALF_STRIDE over the stance.
    x_st = -HALF_STRIDE + 2.0 * HALF_STRIDE * u_st
    x_sw = HALF_STRIDE - 2.0 * HALF_STRIDE * ease(u_sw)
    y_st = np.full_like(p, ANKLE_GROUND)
    y_sw = ANKLE_GROUND - FOOT_LIFT * np.sin(np.pi * u_sw) ** 0.85
    return np.where(stance, x_st, x_sw), np.where(stance, y_st, y_sw), stance


def solve_leg(hip: np.ndarray, target: np.ndarray, l1: float, l2: float, side: float = -1.0):
    """Two-bone IK.  Returns (thigh direction, shin direction) in radians."""
    d = target - hip
    dist = np.clip(np.hypot(d[0], d[1]), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    base = np.arctan2(d[1], d[0])
    cos_a = np.clip((dist * dist + l1 * l1 - l2 * l2) / (2.0 * dist * l1), -1.0, 1.0)
    a = np.arccos(cos_a)
    thigh = base + side * a
    knee = hip + l1 * np.array([np.cos(thigh), np.sin(thigh)])
    shin = np.arctan2(target[1] - knee[1], target[0] - knee[0])
    return thigh, shin


def foot_roll(p: np.ndarray) -> np.ndarray:
    """Ankle angle through the cycle: heel-strike, flat, toe-off, level in swing."""
    p = p % 1.0
    roll = np.zeros_like(p)
    heel = np.clip(1.0 - p / 0.14, 0.0, 1.0)  # toe still up just after landing
    toe = np.clip((p - STANCE + 0.16) / 0.16, 0.0, 1.0) * (p < STANCE)
    swing = np.clip((p - STANCE) / 0.22, 0.0, 1.0) * (p >= STANCE)
    roll += 9.0 * ease(heel)
    roll -= 22.0 * ease(toe)
    roll += 22.0 * ease(swing)  # snap level again for the next landing
    return roll


def blink_track(frames: int, fps: int, period: float = 3.4, seed: int = 7) -> np.ndarray:
    """0 = open, 1 = shut.  Irregular, and fast enough to read as involuntary."""
    rng = np.random.default_rng(seed)
    out = np.zeros(frames, np.float32)
    t = 0.6
    while t < frames / fps + 1.0:
        start = int(t * fps)
        # A real blink is ~6 frames at 24fps: 2 down, 1 held, 3 up.
        shape = [0.35, 1.0, 1.0, 0.8, 0.45, 0.15]
        for k, v in enumerate(shape):
            if 0 <= start + k < frames:
                out[start + k] = max(out[start + k], v)
        t += period * float(rng.uniform(0.55, 1.65))
    return out
