"""
Tests for per-user progress aggregation (src/core/progress.py).

    pytest tests/test_progress.py
    python tests/test_progress.py
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.progress import build_progress, find_user_session_csvs  # noqa: E402


def _write_session(folder: Path, name: str, jitter: float):
    """Write a session CSV; smaller jitter -> steadier gaze -> higher focus score."""
    path = folder / f"alice_{name}_session.csv"
    t0 = 1_700_000_000.0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "x", "y"])
        w.writeheader()
        for i in range(200):
            w.writerow({"timestamp": t0 + i / 20.0,
                        "x": 640 + (i % 2) * jitter,
                        "y": 360 + (i % 2) * jitter})
    return path


def test_find_and_order_sessions():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _write_session(folder, "20260101_090000", 2)
        _write_session(folder, "20260102_090000", 2)
        found = find_user_session_csvs(str(folder))
        assert len(found) == 2
        assert found[0].endswith("20260101_090000_session.csv")  # chronological


def test_build_progress_trend_improves():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _write_session(folder, "20260101_090000", 400)  # jumpy -> low focus
        _write_session(folder, "20260102_090000", 2)    # steady -> high focus
        report, scored = build_progress(str(folder))
        assert report.session_count == 2
        assert len(scored) == 2
        assert report.last_score > report.first_score
        assert report.trend == "Improving"


def test_build_progress_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        report, scored = build_progress(tmp)
        assert report.session_count == 0
        assert scored == []
    # non-existent dir is handled too
    assert find_user_session_csvs(None) == []


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
