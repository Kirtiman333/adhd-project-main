"""
End-to-end tests for the gaze inference pipeline (src/vision/eye_tracker.py),
using a fake estimator/smoother so no camera, eyetrax, or pygame is needed.

Exercises the accuracy-critical path: monitor->surface scaling and outlier
rejection.

    pytest tests/test_eye_tracker.py
    python tests/test_eye_tracker.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vision.eye_tracker import EyeTracker, _IdentitySmoother  # noqa: E402


class FakeEstimator:
    """Scripted stand-in for eyetrax's GazeEstimator."""
    def __init__(self, features_seq, predict_seq):
        self.features_seq = list(features_seq)   # list of (features, blink)
        self.predict_seq = list(predict_seq)     # list of (x, y) monitor-space points

    def extract_features(self, frame):
        return self.features_seq.pop(0)

    def predict(self, arr):
        return [self.predict_seq.pop(0)]


def _tracker(features_seq, predict_seq):
    return EyeTracker(
        estimator=FakeEstimator(features_seq, predict_seq),
        smoother=_IdentitySmoother(),
        monitor_size=(1920, 1080),     # different from the 1280x720 surface
    )


def test_prediction_is_scaled_monitor_to_surface():
    # Monitor-space (960,540) is the screen center -> surface center (640,360).
    t = _tracker([([1.0], False)], [(960, 540)])
    s = t.update("frame")
    assert s.pred_x == 640 and s.pred_y == 360
    assert s.cursor_alpha > 0


def test_blink_yields_no_point():
    t = _tracker([([1.0], True)], [(960, 540)])
    s = t.update("frame")
    assert s.pred_x is None and s.pred_y is None
    assert s.blink_detected is True


def test_outlier_jump_is_rejected():
    # First a near-origin gaze, then a glitch spike across the screen.
    t = _tracker([([1.0], False), ([1.0], False)],
                 [(100, 100), (1900, 1060)])
    s1 = t.update("frame")
    assert s1.pred_x is not None                      # first point accepted
    s2 = t.update("frame")
    assert s2.pred_x is None                           # implausible jump rejected
    assert t.gaze_filter.rejected == 1


def test_validate_returns_accuracy_report():
    t = _tracker([], [])
    perfect = t.validate([((100, 100), (100, 100)), ((640, 360), (640, 360))])
    assert perfect.accuracy_score == 100.0
    assert perfect.passed is True


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
