"""
Tests for SessionRecorder: recording, CSV save, and the recorder->scorer
integration (score_session).

    pytest tests/test_session_recorder.py
    python tests/test_session_recorder.py
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.session_recorder import SessionRecorder  # noqa: E402


def _recorder(tmp):
    user = SimpleNamespace(username="tester", session_path=tmp, heatmap_path=tmp)
    return SessionRecorder(user)


def test_record_skips_none_and_coerces_int():
    with tempfile.TemporaryDirectory() as tmp:
        r = _recorder(tmp)
        r.record(None, 5)
        r.record(5, None)
        r.record(10.7, 20.2)
        assert len(r.current_data) == 1
        assert r.current_data[0]["x"] == 10 and r.current_data[0]["y"] == 20


def test_save_session_empty_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        r = _recorder(tmp)
        assert r.save_session() is None


def test_save_session_writes_csv_and_clears():
    with tempfile.TemporaryDirectory() as tmp:
        r = _recorder(tmp)
        for i in range(5):
            r.record(100 + i, 200 + i)
        path = r.save_session()
        assert path and Path(path).exists()
        assert r.current_data == []  # cleared after save

        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert set(rows[0].keys()) == {"timestamp", "x", "y"}
        assert len(rows) == 5


def test_score_session_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        r = _recorder(tmp)
        # Write a focused gaze CSV in the exact format save_session() produces.
        path = Path(tmp) / "tester_focused_session.csv"
        t0 = 1_700_000_000.0
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timestamp", "x", "y"])
            w.writeheader()
            for i in range(200):  # ~10s at 20 Hz, steady gaze near a point
                w.writerow({"timestamp": t0 + i / 20.0, "x": 640 + (i % 3), "y": 360 + (i % 3)})

        m = r.score_session(str(path))
        assert m is not None
        assert m.sample_count == 200
        assert m.focus_score > 50         # steady gaze => strong focus
        assert 0.0 <= m.focus_ratio <= 1.0


def test_score_session_missing_path():
    with tempfile.TemporaryDirectory() as tmp:
        r = _recorder(tmp)
        assert r.score_session(None) is None
        assert r.score_session(str(Path(tmp) / "nope.csv")) is None


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
