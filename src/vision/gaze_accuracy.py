"""
Gaze accuracy measurement.

The gaze model is the product's sensor — the heatmap, focus score, and adaptive
difficulty are all downstream of it — but nothing in the project measured how
accurate it actually is. This module makes accuracy a number.

Given validation pairs of (predicted_point, target_point) in screen pixels
(e.g. collected by showing the player a dot and recording where the model
thinks they looked), `accuracy_metrics` returns error statistics and a 0–100
accuracy score, plus a pass/fail against a pixel tolerance. Used for:

  * the post-calibration validation pass (accept / re-calibrate),
  * persisting a per-user `calibration_error`,
  * a regression harness so accuracy can't silently degrade.

Pure standard library — fully unit-testable, no camera or eyetrax needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import List, Sequence, Tuple

from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, CALIBRATION_MAX_ERROR_PX

Point = Tuple[float, float]
Pair = Tuple[Point, Point]  # (predicted, target)


@dataclass
class AccuracyReport:
    n: int = 0
    mean_error_px: float = 0.0
    rmse_px: float = 0.0
    p95_error_px: float = 0.0
    max_error_px: float = 0.0
    within_tolerance_ratio: float = 0.0   # fraction of points within `tolerance_px`
    tolerance_px: float = 0.0
    accuracy_score: float = 0.0           # 0..100 (higher = better)
    passed: bool = False
    region_error_px: dict = field(default_factory=dict)  # 3x3 grid mean error

    def as_dict(self) -> dict:
        return asdict(self)


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _percentile(sorted_vals: Sequence[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _region(pt: Point, w: int, h: int) -> str:
    col = min(2, max(0, int(pt[0] / max(1, w) * 3)))
    row = min(2, max(0, int(pt[1] / max(1, h) * 3)))
    names = ["top", "mid", "bot"], ["left", "center", "right"]
    return f"{names[0][row]}-{names[1][col]}"


def accuracy_metrics(
    pairs: Sequence[Pair],
    screen: Tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT),
    tolerance_px: float = CALIBRATION_MAX_ERROR_PX,
) -> AccuracyReport:
    """Compute accuracy stats from (predicted, target) pixel pairs."""
    if not pairs:
        return AccuracyReport(tolerance_px=tolerance_px)

    w, h = screen
    diag = math.hypot(w, h)
    errors = [_dist(pred, tgt) for pred, tgt in pairs]
    errors_sorted = sorted(errors)

    mean_err = sum(errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    within = sum(1 for e in errors if e <= tolerance_px) / len(errors)

    # Per-region mean error (keyed by the *target* location).
    region_sum: dict = {}
    region_cnt: dict = {}
    for (pred, tgt), e in zip(pairs, errors):
        r = _region(tgt, w, h)
        region_sum[r] = region_sum.get(r, 0.0) + e
        region_cnt[r] = region_cnt.get(r, 0) + 1
    region_error = {r: round(region_sum[r] / region_cnt[r], 1) for r in region_sum}

    # Accuracy score: error of 0 -> 100; error of 25% of the diagonal -> 0.
    norm = 1.0 - min(1.0, mean_err / (0.25 * diag))
    score = round(100.0 * max(0.0, norm), 1)

    return AccuracyReport(
        n=len(errors),
        mean_error_px=round(mean_err, 1),
        rmse_px=round(rmse, 1),
        p95_error_px=round(_percentile(errors_sorted, 0.95), 1),
        max_error_px=round(errors_sorted[-1], 1),
        within_tolerance_ratio=round(within, 3),
        tolerance_px=tolerance_px,
        accuracy_score=score,
        passed=mean_err <= tolerance_px,
        region_error_px=region_error,
    )
