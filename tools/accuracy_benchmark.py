"""
Gaze accuracy benchmark — estimate the impact of the accuracy fixes.

IMPORTANT: this is a *simulation*, not a measurement on real hardware (eyetrax +
a webcam are required for the on-device validation pass). It models the error
sources each change addresses, so the relative before/after deltas are meaningful
even though the absolute numbers are estimates. Every assumption is stated below
and is deterministic (seeded).

Pipelines compared, each adding one change on top of the previous:
  1. Initial            — eyetrax's monitor-resolution predictions used directly
                          in the 1280x720 surface (no scaling), no outlier filter,
                          5-point calibration. Points landing past the surface
                          bounds are dropped exactly as SessionRecorder's heatmap
                          drops them (`0 <= x < 1280`).
  2. + coordinate scale — map monitor-space -> surface-space.
  3. + outlier filter   — reject impossible jumps / spikes.
  4. + 9-pt calibration — denser calibration lowers the model's base error.

Assumptions (stated so they can be challenged):
  * monitor 1920x1080, game surface 1280x720 (scale factor 1.5).
  * webcam gaze base error ~100 px (5-pt) / ~65 px (9-pt) in monitor pixels
    (~2-3 deg vs ~1.5 deg — typical for webcam trackers).
  * 6% of frames are tracking-glitch spikes.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vision.gaze_accuracy import accuracy_metrics
from src.vision.gaze_filter import scale_point, GazeFilter

SURFACE = (1280, 720)
MONITOR = (1920, 1080)
SCALE = (MONITOR[0] / SURFACE[0], MONITOR[1] / SURFACE[1])  # 1.5, 1.5

CAL_STD_5PT = 100.0   # monitor-px calibration noise, 5-point
CAL_STD_9PT = 65.0    # monitor-px calibration noise, 9-point
SPIKE_RATE = 0.06
SEED = 20260609
N_REPEATS = 40        # samples per target


def _targets():
    """A 9-point validation grid in surface coordinates (where the user looks)."""
    xs = [SURFACE[0] * f for f in (0.15, 0.5, 0.85)]
    ys = [SURFACE[1] * f for f in (0.15, 0.5, 0.85)]
    return [(x, y) for y in ys for x in xs]


def _simulate(cal_std, seed):
    """Return a list of (target_surface, raw_prediction_monitorspace) samples."""
    rng = random.Random(seed)
    samples = []
    for tx, ty in _targets():
        # The model is calibrated/predicts in monitor space; the monitor location
        # of a surface target is (tx*scale_x, ty*scale_y).
        mx, my = tx * SCALE[0], ty * SCALE[1]
        for _ in range(N_REPEATS):
            if rng.random() < SPIKE_RATE:
                # tracking glitch: gaze momentarily jumps to a random monitor location
                px, py = rng.uniform(0, MONITOR[0]), rng.uniform(0, MONITOR[1])
            else:
                px = mx + rng.gauss(0, cal_std)
                py = my + rng.gauss(0, cal_std)
            samples.append(((tx, ty), (px, py)))
    return samples


def _pipeline_initial(samples):
    """Monitor coords used directly as surface coords; off-surface points dropped."""
    pairs = []
    total = len(samples)
    for target, pred in samples:
        x, y = pred  # used as-is, no scaling
        if 0 <= x < SURFACE[0] and 0 <= y < SURFACE[1]:   # heatmap/scorer drop rule
            pairs.append(((x, y), target))
    return pairs, total


def _pipeline_scaled(samples, use_filter):
    """Scale monitor->surface; optionally run the outlier filter over the stream."""
    pairs = []
    total = len(samples)
    filt = GazeFilter(screen=SURFACE) if use_filter else None
    for target, pred in samples:
        sx, sy = scale_point(pred, MONITOR, SURFACE)
        if filt is not None:
            pt = filt.step(sx, sy)
            if pt is None:
                continue
            sx, sy = pt
        else:
            # still clamp to surface (a point can't be off-screen), matching reality
            sx = min(max(0.0, sx), SURFACE[0] - 1)
            sy = min(max(0.0, sy), SURFACE[1] - 1)
        pairs.append(((sx, sy), target))
    return pairs, total


def _row(name, pairs, total):
    r = accuracy_metrics(pairs, screen=SURFACE)
    retained = 100.0 * len(pairs) / total if total else 0.0
    return {
        "name": name,
        "retained": retained,
        "mean": r.mean_error_px,
        "rmse": r.rmse_px,
        "within": r.within_tolerance_ratio * 100.0,
        "score": r.accuracy_score,
    }


def main():
    base = _simulate(CAL_STD_5PT, SEED)
    base9 = _simulate(CAL_STD_9PT, SEED)

    rows = [
        _row("1. Initial (no fixes)", *_pipeline_initial(base)),
        _row("2. + coordinate scaling", *_pipeline_scaled(base, use_filter=False)),
        _row("3. + outlier filter", *_pipeline_scaled(base, use_filter=True)),
        _row("4. + 9-pt calibration", *_pipeline_scaled(base9, use_filter=True)),
    ]

    print("=" * 78)
    print("  GAZE ACCURACY BENCHMARK  (simulation - see module docstring for assumptions)")
    print(f"  monitor {MONITOR[0]}x{MONITOR[1]} -> surface {SURFACE[0]}x{SURFACE[1]} "
          f"| {len(base)} samples | tolerance {int(accuracy_metrics([],SURFACE).tolerance_px)}px")
    print("=" * 78)
    print(f"  {'pipeline':<32}{'kept%':>7}{'mean px':>9}{'rmse':>7}{'<=tol%':>7}{'score':>7}")
    print("  " + "-" * 69)
    for r in rows:
        print(f"  {r['name']:<32}{r['retained']:>6.0f}%{r['mean']:>9.0f}{r['rmse']:>7.0f}"
              f"{r['within']:>6.0f}%{r['score']:>7.1f}")
    print("  " + "-" * 69)

    first, last = rows[0], rows[-1]
    print(f"\n  Overall accuracy score: {first['score']:.1f}  ->  {last['score']:.1f}  "
          f"(+{last['score'] - first['score']:.1f})")
    print(f"  Mean error:  {first['mean']:.0f}px  ->  {last['mean']:.0f}px  "
          f"({100*(first['mean']-last['mean'])/first['mean']:.0f}% lower)")
    print(f"  Usable gaze samples kept:  {first['retained']:.0f}%  ->  {last['retained']:.0f}%")
    print("\n  NOTE: simulation, not hardware-measured. Real validation = the")
    print("  on-device calibration check (pending eyetrax + webcam).")


if __name__ == "__main__":
    main()
