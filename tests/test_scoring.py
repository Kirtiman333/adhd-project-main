"""
Tests for the attention scorer.

Runnable two ways:
    pytest tests/test_scoring.py
    python tests/test_scoring.py        # no pytest needed
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game_logic.scoring import AttentionScorer, SessionMetrics  # noqa: E402


def _focused_stream(hz=20, seconds=20):
    """Gaze that holds steady near one point -> high focus."""
    t0 = 1_700_000_000.0
    cx, cy = 640, 360
    pts = []
    for i in range(hz * seconds):
        # tiny deterministic jitter well inside the fixation radius
        x = cx + 8 * math.sin(i / 5)
        y = cy + 8 * math.cos(i / 5)
        pts.append((t0 + i / hz, x, y))
    return pts


def _distracted_stream(hz=20, seconds=20):
    """Gaze that jumps far every few samples -> low focus, many distractions."""
    t0 = 1_700_000_000.0
    pts = []
    for i in range(hz * seconds):
        # large deterministic swings across the screen
        x = 640 + 560 * math.sin(i / 1.3)
        y = 360 + 320 * math.cos(i / 1.1)
        pts.append((t0 + i / hz, x, y))
    return pts


def test_focused_beats_distracted():
    scorer = AttentionScorer()
    focused = scorer.score(_focused_stream())
    distracted = scorer.score(_distracted_stream())
    assert focused.focus_score > distracted.focus_score, (
        f"focused {focused.focus_score} should beat distracted {distracted.focus_score}"
    )
    # A steady gaze should be clearly above the midpoint; a jumpy one clearly below.
    assert focused.focus_score >= 60
    assert distracted.focus_score <= 45


def test_metric_bounds_and_basics():
    scorer = AttentionScorer()
    m = scorer.score(_focused_stream())
    assert 0.0 <= m.focus_ratio <= 1.0
    assert 0.0 <= m.focus_score <= 100.0
    assert m.duration_s > 0
    assert m.sample_count == 400
    assert m.fixation_count >= 1
    assert m.longest_focus_s > 0


def test_distraction_events_detected():
    scorer = AttentionScorer()
    m = scorer.score(_distracted_stream())
    assert m.distraction_events > 0
    assert m.distraction_rate_hz > 0


def test_handles_degenerate_input():
    scorer = AttentionScorer()
    assert scorer.score([]).sample_count == 0
    assert scorer.score([(1.0, 100.0, 100.0)]).sample_count == 1  # single point, no crash
    # all samples at the same timestamp -> zero duration, handled gracefully
    zero_dur = scorer.score([(5.0, 1, 1), (5.0, 2, 2), (5.0, 3, 3)])
    assert zero_dur.focus_score == 0.0


def test_progress_trend():
    scorer = AttentionScorer()
    low = scorer.score(_distracted_stream())
    high = scorer.score(_focused_stream())
    report = scorer.summarize_progress([("s1", low), ("s2", high)])
    assert report.session_count == 2
    assert report.trend == "Improving"
    assert report.delta > 0
    assert report.best_score == high.focus_score


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
