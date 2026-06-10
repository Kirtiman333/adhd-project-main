"""
Tests for threaded webcam capture (src/vision/camera_threading.py), using an
injected fake capture device so no real camera is needed.

    pytest tests/test_camera_threading.py
    python tests/test_camera_threading.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vision.camera_threading import CameraThreading  # noqa: E402


class FakeCap:
    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self._opened = opened
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self.frames:
            return True, self.frames.pop(0)
        return False, None

    def release(self):
        self.released = True
        self._opened = False


def test_grab_once_and_read_returns_copy():
    cap = FakeCap([np.array([[1, 2], [3, 4]])])
    ct = CameraThreading(cap=cap)
    assert ct.is_opened()
    assert ct.read() is None                 # nothing grabbed yet
    assert ct._grab_once() is True
    r = ct.read()
    assert r is not None
    assert r is not ct.frame                  # a copy, not the shared buffer
    assert (r == ct.frame).all()
    ct.stop()
    assert cap.released is True


def test_read_failure_counts_and_caps():
    cap = FakeCap([])                         # always fails to read
    ct = CameraThreading(cap=cap)
    assert ct._grab_once() is False
    assert ct._read_failures == 1


def test_unavailable_camera_does_not_start_thread():
    cap = FakeCap([], opened=False)
    ct = CameraThreading(cap=cap)
    assert ct.is_opened() is False
    ct.start()
    assert ct.is_running is False             # refused to spawn a grabber thread
    assert ct._thread is None
    ct.stop()


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
