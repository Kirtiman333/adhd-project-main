"""
Attention scoring for recorded gaze sessions.

The app already records, per play session, a stream of predicted gaze points
(timestamp, x, y) to a CSV (see src/core/session_recorder.py) and turns it into
a heatmap. A heatmap shows *where* the eyes went, but not *how well the player
sustained attention* — which is the whole point of an ADHD training tool.

This module turns that same raw gaze stream into interpretable attention
metrics, and turns a sequence of sessions into a progress trend. It is pure
standard-library (math/csv/statistics) on purpose: no pygame, no pandas, no
numpy — so it stays fast, trivially testable, and runnable on any machine
regardless of the game runtime.

Metric model (simplified I-DT / dispersion-threshold eye-tracking approach):
  * A *fixation* is a run of consecutive samples where the gaze barely moves
    (step distance <= fixation_radius px). Fixations are the building block of
    sustained attention.
  * A *saccade / distraction event* is a large jump between samples
    (> saccade_threshold px) — a proxy for distractibility / impulsive shifts.
  * focus_ratio   = time spent in fixations / total session time  (sustained attention)
  * dispersion    = mean distance of all samples from their centroid (spatial concentration)
  * focus_score   = transparent 0–100 blend of the three (weights documented below)

Thresholds default to a 1280x720 screen (src/config.py) and are constructor
arguments so they can be tuned per display or per user.
"""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Sequence, Tuple

# Defaults mirror src/config.py (SCREEN_WIDTH / SCREEN_HEIGHT) without importing
# it, so this module has zero project dependencies and runs standalone.
DEFAULT_SCREEN = (1280, 720)

GazeSample = Tuple[float, float, float]  # (timestamp_seconds, x_px, y_px)


@dataclass
class SessionMetrics:
    """Attention metrics for a single play session."""
    sample_count: int = 0
    duration_s: float = 0.0
    sampling_hz: float = 0.0
    fixation_count: int = 0
    mean_fixation_s: float = 0.0
    longest_focus_s: float = 0.0          # longest single fixation = peak sustained attention
    focus_ratio: float = 0.0              # 0..1, share of time in fixations
    distraction_events: int = 0           # large gaze jumps (saccades over threshold)
    distraction_rate_hz: float = 0.0      # distraction events per second
    dispersion_px: float = 0.0            # mean distance from gaze centroid
    focus_score: float = 0.0              # 0..100 composite
    label: str = "no data"               # human-readable bucket
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProgressReport:
    """Trend across several sessions for one user — the long-term value view."""
    session_count: int = 0
    first_score: float = 0.0
    last_score: float = 0.0
    best_score: float = 0.0
    mean_score: float = 0.0
    delta: float = 0.0                    # last - first
    trend: str = "no data"               # Improving / Stable / Declining
    per_session: List[Tuple[str, float]] = field(default_factory=list)  # (label, focus_score)


def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _bucket(score: float) -> str:
    if score >= 75:
        return "Strong focus"
    if score >= 55:
        return "Moderate focus"
    if score >= 35:
        return "Distractible"
    return "Highly distractible"


class AttentionScorer:
    """Compute attention metrics from a gaze stream.

    All thresholds are in pixels (for the configured screen) or seconds and can
    be tuned per display / per user.
    """

    def __init__(
        self,
        screen: Tuple[int, int] = DEFAULT_SCREEN,
        fixation_radius_px: float = 45.0,
        saccade_threshold_px: float = 220.0,
        min_fixation_samples: int = 3,
    ):
        self.screen = screen
        self.fixation_radius_px = fixation_radius_px
        self.saccade_threshold_px = saccade_threshold_px
        self.min_fixation_samples = max(2, min_fixation_samples)
        self._diag = math.hypot(*screen)

    # ---- public API ------------------------------------------------------

    def score(self, samples: Sequence[GazeSample]) -> SessionMetrics:
        """Score an in-memory gaze stream of (timestamp, x, y) tuples."""
        pts = [(float(t), float(x), float(y)) for t, x, y in samples]
        pts.sort(key=lambda s: s[0])

        if len(pts) < 2:
            return SessionMetrics(sample_count=len(pts), note="not enough samples to score")

        duration = pts[-1][0] - pts[0][0]
        if duration <= 0:
            return SessionMetrics(sample_count=len(pts), note="zero-duration session")

        xy = [(p[1], p[2]) for p in pts]
        steps = [_euclidean(xy[i], xy[i - 1]) for i in range(1, len(xy))]

        fixations = self._detect_fixations(pts)
        focus_time = sum(d for _, _, d in fixations)
        distractions = sum(1 for s in steps if s > self.saccade_threshold_px)

        cx = statistics.fmean(p[1] for p in pts)
        cy = statistics.fmean(p[2] for p in pts)
        dispersion = statistics.fmean(_euclidean((p[1], p[2]), (cx, cy)) for p in pts)

        focus_ratio = _clamp(focus_time / duration, 0.0, 1.0)
        distraction_rate = distractions / duration

        m = SessionMetrics(
            sample_count=len(pts),
            duration_s=round(duration, 2),
            sampling_hz=round(len(pts) / duration, 1),
            fixation_count=len(fixations),
            mean_fixation_s=round(statistics.fmean(d for _, _, d in fixations), 3) if fixations else 0.0,
            longest_focus_s=round(max((d for _, _, d in fixations), default=0.0), 3),
            focus_ratio=round(focus_ratio, 3),
            distraction_events=distractions,
            distraction_rate_hz=round(distraction_rate, 3),
            dispersion_px=round(dispersion, 1),
        )
        m.focus_score = self._focus_score(focus_ratio, distraction_rate, dispersion)
        m.label = _bucket(m.focus_score)
        return m

    def score_csv(self, path) -> SessionMetrics:
        """Score a session CSV with columns: timestamp, x, y (as written by SessionRecorder)."""
        return self.score(self._read_csv(path))

    def summarize_progress(self, scored_sessions: Sequence[Tuple[str, SessionMetrics]]) -> ProgressReport:
        """Aggregate ordered (label, metrics) pairs into a trend.

        `scored_sessions` should be in chronological order (oldest first).
        """
        usable = [(lbl, m) for lbl, m in scored_sessions if m.sample_count >= 2]
        if not usable:
            return ProgressReport()

        scores = [m.focus_score for _, m in usable]
        first, last = scores[0], scores[-1]
        delta = round(last - first, 1)

        if len(scores) < 2 or abs(delta) < 5:
            trend = "Stable"
        elif delta > 0:
            trend = "Improving"
        else:
            trend = "Declining"

        return ProgressReport(
            session_count=len(usable),
            first_score=first,
            last_score=last,
            best_score=max(scores),
            mean_score=round(statistics.fmean(scores), 1),
            delta=delta,
            trend=trend,
            per_session=[(lbl, m.focus_score) for lbl, m in usable],
        )

    # ---- internals -------------------------------------------------------

    def _detect_fixations(self, pts: Sequence[GazeSample]) -> List[Tuple[int, int, float]]:
        """Return fixations as (start_idx, end_idx, duration_s).

        A fixation is a maximal run of consecutive samples connected by steps no
        larger than fixation_radius_px, lasting at least min_fixation_samples.
        """
        fixations: List[Tuple[int, int, float]] = []
        start = 0
        for i in range(1, len(pts)):
            step = _euclidean((pts[i][1], pts[i][2]), (pts[i - 1][1], pts[i - 1][2]))
            if step > self.fixation_radius_px:
                self._maybe_add_fixation(pts, start, i - 1, fixations)
                start = i
        self._maybe_add_fixation(pts, start, len(pts) - 1, fixations)
        return fixations

    def _maybe_add_fixation(self, pts, start, end, out):
        if end - start + 1 >= self.min_fixation_samples:
            out.append((start, end, pts[end][0] - pts[start][0]))

    def _focus_score(self, focus_ratio: float, distraction_rate: float, dispersion: float) -> float:
        """Transparent 0–100 composite of three attention dimensions.

        sustained     (50%): time spent fixating  -> focus_ratio
        steadiness    (30%): freedom from distraction jumps -> 1 - normalized distraction rate
        concentration (20%): spatial tightness of gaze -> 1 - normalized dispersion

        The two caps below define "as bad as it gets" for normalization:
          * 3 distraction jumps/sec saturates steadiness to 0
          * dispersion of 35% of the screen diagonal saturates concentration to 0
        """
        sustained = focus_ratio
        steadiness = 1.0 - _clamp(distraction_rate / 3.0, 0.0, 1.0)
        concentration = 1.0 - _clamp(dispersion / (0.35 * self._diag), 0.0, 1.0)
        score = 100.0 * (0.50 * sustained + 0.30 * steadiness + 0.20 * concentration)
        return round(score, 1)

    def _read_csv(self, path) -> List[GazeSample]:
        out: List[GazeSample] = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    out.append((float(row["timestamp"]), float(row["x"]), float(row["y"])))
                except (KeyError, ValueError, TypeError):
                    continue  # skip malformed / header-only rows
        return out
