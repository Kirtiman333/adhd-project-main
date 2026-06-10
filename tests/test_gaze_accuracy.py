"""
Tests for gaze accuracy metrics + coordinate scaling / filtering.

    pytest tests/test_gaze_accuracy.py
    python tests/test_gaze_accuracy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vision.gaze_accuracy import accuracy_metrics  # noqa: E402
from src.vision.gaze_filter import scale_point, clamp_point, GazeFilter  # noqa: E402

SCREEN = (1280, 720)


def test_perfect_accuracy():
    targets = [(100, 100), (640, 360), (1100, 600)]
    pairs = [(t, t) for t in targets]      # predicted == target
    r = accuracy_metrics(pairs, screen=SCREEN)
    assert r.n == 3
    assert r.mean_error_px == 0.0
    assert r.accuracy_score == 100.0
    assert r.passed is True
    assert r.within_tolerance_ratio == 1.0


def test_offset_reduces_score():
    targets = [(640, 360), (200, 200), (1000, 500)]
    pairs = [((tx + 30, ty + 40), (tx, ty)) for tx, ty in targets]  # 50px off each
    r = accuracy_metrics(pairs, screen=SCREEN)
    assert abs(r.mean_error_px - 50.0) < 0.5
    assert 0 < r.accuracy_score < 100
    assert set(r.region_error_px.keys())          # region breakdown present


def test_empty_pairs():
    r = accuracy_metrics([], screen=SCREEN)
    assert r.n == 0
    assert r.accuracy_score == 0.0


def test_fails_when_beyond_tolerance():
    pairs = [((0, 0), (500, 500))]                 # huge error
    r = accuracy_metrics(pairs, screen=SCREEN, tolerance_px=120)
    assert r.passed is False
    assert r.max_error_px > 120


def test_scale_point_and_clamp():
    # 1920x1080 monitor center -> 1280x720 surface center
    assert scale_point((960, 540), (1920, 1080), (1280, 720)) == (640.0, 360.0)
    assert clamp_point((-5, 5000), (1280, 720)) == (0.0, 719.0)


def test_gaze_filter_rejects_blink_none_and_jumps():
    f = GazeFilter(screen=SCREEN, max_jump_ratio=0.6)
    assert f.step(None, 10) is None
    assert f.step(10, 10, blink=True) is None
    assert f.step(100, 100) == (100.0, 100.0)      # first valid point accepted
    # a jump across most of the screen is rejected as a glitch
    assert f.step(1270, 700) is None
    assert f.rejected == 1
    # a small move from the last accepted point is fine
    assert f.step(110, 110) == (110.0, 110.0)


def test_gaze_filter_recovers_after_persistent_relocation():
    # A genuine fast look across the screen must not freeze the filter forever.
    f = GazeFilter(screen=SCREEN, max_jump_ratio=0.6, max_consecutive_rejects=3)
    assert f.step(50, 360) == (50.0, 360.0)
    assert f.step(1270, 360) is None     # 1st big jump -> dropped as glitch
    assert f.step(1265, 365) is None     # 2nd -> still dropped
    accepted = f.step(1268, 360)         # 3rd consecutive -> accept the relocation
    assert accepted is not None
    assert f.step(1270, 362) is not None  # now tracking near the new location


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
