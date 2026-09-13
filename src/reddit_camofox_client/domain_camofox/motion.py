"""Pure scroll-trajectory math: no page/DOM access, no I/O.

Ported from ui-kit/scripts/video-agent/src/capability/scroll_math.py
(HumanJS planScroll port): bell-curve-velocity wheel deltas, ease-in /
ease-out, normalised so the deltas sum to the distance exactly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class ScrollStep:
    """One wheel delta in a human scroll trajectory."""

    delta_y: float
    delay_ms: int


def _bell_phase(
    distance: float,
    *,
    segments_per_kpx: float = 18.0,
    segment_delay_ms: float = 32.0,
    delay_jitter: float = 0.20,
    rng: random.Random,
) -> list[ScrollStep]:
    """Half-sine-weighted segments: accelerate from rest, peak mid-way,
    decelerate to a stop. Short scrolls collapse to fast flicks; long
    scrolls keep the full ramp. Delays never drop below 12ms (faster
    reads as a teleport, not a scroll)."""
    if distance == 0:
        return []

    abs_dist = abs(distance)
    count = max(1, math.ceil(abs_dist / 1000.0 * segments_per_kpx))

    short_floor_ms = 12.0
    long_full_ms = segment_delay_ms
    long_ref_px = 5000.0
    if abs_dist >= long_ref_px:
        delay_base = long_full_ms
    else:
        t = math.log1p(abs_dist) / math.log1p(long_ref_px)
        delay_base = short_floor_ms + (long_full_ms - short_floor_ms) * t

    direction = 1.0 if distance > 0 else -1.0
    weights = [math.sin(((i + 0.5) / count) * math.pi) for i in range(count)]
    total_weight = sum(weights)

    steps: list[ScrollStep] = []
    for weight in weights:
        delta = direction * abs(distance) * weight / total_weight
        delay = max(12, int(delay_base * rng.uniform(1.0 - delay_jitter, 1.0 + delay_jitter)))
        steps.append(ScrollStep(delta_y=delta, delay_ms=delay))
    return steps


def human_scroll_trajectory(
    distance: float,
    *,
    seed: int | None = None,
) -> list[ScrollStep]:
    """Bell-curve scroll plan with overshoot and recoil.

    Forward bell phase runs to target + overshoot (larger fraction on
    short flicks, smaller on long scrolls), then a shorter reverse phase
    recoils back to the target. Sparse mid-scroll pauses (never in the
    recoil) keep it from reading as a metronome.
    """
    rng = random.Random(seed)
    if not distance:
        return []

    direction = 1 if distance > 0 else -1
    abs_dist = abs(distance)

    short_overshoot = 0.25
    long_overshoot = 0.03
    long_ref_px = 5000.0
    if abs_dist >= long_ref_px:
        fraction = long_overshoot
    else:
        t = math.log1p(abs_dist) / math.log1p(long_ref_px)
        fraction = short_overshoot + (long_overshoot - short_overshoot) * t
    extra = abs_dist * fraction

    forward = _bell_phase(abs_dist + extra, rng=rng)
    reverse = (
        _bell_phase(extra, segments_per_kpx=10.0, segment_delay_ms=20.0, rng=rng)
        if extra >= 1.0
        else []
    )
    steps = forward + reverse

    fwd_len = len(forward)
    result: list[ScrollStep] = []
    for idx, step in enumerate(steps):
        is_fwd = idx < fwd_len
        d = direction if is_fwd else -direction
        result.append(ScrollStep(delta_y=step.delta_y * d, delay_ms=step.delay_ms))
        if 0 < idx < fwd_len - 1 and rng.random() < 0.08:
            result.append(ScrollStep(delta_y=0.0, delay_ms=rng.randint(100, 240)))
    return result
