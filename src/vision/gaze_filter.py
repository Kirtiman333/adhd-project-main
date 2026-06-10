"""
Gaze coordinate scaling + outlier rejection.

Handles two accuracy-affecting concerns in the gaze path:

1. **Scale mismatch.** eyetrax predicts in the *calibration monitor's*
   resolution (e.g. 1920x1080), but the game window and the heatmap/scorer work
   in the pygame surface space (1280x720, see config). Unscaled points landed
   off-canvas and were silently dropped by the heatmap (`x>=1280`) and
   mis-normalized by the scorer. `scale_point` maps monitor space -> surface
   space so every prediction counts and lines up with what was drawn.

2. **Noise / impossible jumps.** Raw per-frame predictions occasionally spike
   far across the screen (tracking glitch, partial face, etc.). `GazeFilter`
   rejects physically-implausible jumps, drops blink/None frames, and clamps to
   the screen, so cleaner data reaches the recorder and the focus scorer.

Pure standard library — fully unit-testable.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, GAZE_OUTLIER_JUMP_RATIO

Point = Tuple[float, float]


def scale_point(pt: Point, from_size: Tuple[int, int], to_size: Tuple[int, int]) -> Point:
    """Linearly map a point from one resolution to another."""
    fw, fh = from_size
    tw, th = to_size
    x = pt[0] * (tw / fw) if fw else pt[0]
    y = pt[1] * (th / fh) if fh else pt[1]
    return (x, y)


def clamp_point(pt: Point, size: Tuple[int, int]) -> Point:
    """Clamp a point into [0, w-1] x [0, h-1]."""
    w, h = size
    return (min(max(0.0, pt[0]), w - 1), min(max(0.0, pt[1]), h - 1))


class GazeFilter:
    """Reject blink/None/outlier samples and clamp valid ones to the screen.

    `step(x, y, blink)` returns a cleaned (x, y), or None if the sample should be
    discarded (blink, missing, or an implausible jump from the last accepted point).
    """

    def __init__(self, screen: Tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT),
                 max_jump_ratio: float = GAZE_OUTLIER_JUMP_RATIO,
                 max_consecutive_rejects: int = 3):
        self.screen = screen
        self.max_jump = max_jump_ratio * math.hypot(*screen)
        self.max_consecutive_rejects = max(1, max_consecutive_rejects)
        self._last: Optional[Point] = None
        self.rejected = 0
        self._reject_streak = 0

    def step(self, x, y, blink: bool = False) -> Optional[Point]:
        if blink or x is None or y is None:
            return None
        pt = clamp_point((float(x), float(y)), self.screen)
        if self._last is not None:
            jump = math.hypot(pt[0] - self._last[0], pt[1] - self._last[1])
            if jump > self.max_jump:
                self.rejected += 1
                self._reject_streak += 1
                # Drop transient glitches, but if the gaze persistently sits at a
                # new location, accept it as a real relocation (saccade) so the
                # filter can't get stuck on a stale reference point.
                if self._reject_streak < self.max_consecutive_rejects:
                    return None
        self._reject_streak = 0
        self._last = pt
        return pt

    def reset(self) -> None:
        self._last = None
        self.rejected = 0
        self._reject_streak = 0
