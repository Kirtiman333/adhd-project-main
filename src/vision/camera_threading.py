"""
Threaded webcam capture.

A background thread keeps the latest frame available via read(). Design notes:
  * the grab loop is rate-capped to CAM_FPS and gives up after a run of read
    failures, so it never busy-spins a CPU core or loops forever on a dead camera;
  * read() returns a copy, so a consumer can't be torn by the grabber rebinding
    the buffer mid-use;
  * stop() joins the worker before releasing the device (no release-under-read
    race), and start() refuses to spawn a thread when no camera is available;
  * the capture object is injectable (cap=) so the logic is testable without a
    real webcam.
"""

import threading
import time

import cv2

from src.config import CAMERA_ID, CAM_FPS


class CameraThreading:
    def __init__(self, camera_id=CAMERA_ID, cap=None, target_fps=CAM_FPS):
        self.camera_id = camera_id
        self.frame = None
        self.lock = threading.Lock()
        # `cap` is injectable for tests; default opens the real webcam.
        self.cap = cap if cap is not None else cv2.VideoCapture(camera_id)
        self.target_fps = max(1, target_fps)
        self.is_running = True
        self._thread = None
        self._read_failures = 0
        if not self.is_opened():
            print(f"[CameraThreading] WARNING: camera {camera_id} not available")

    def is_opened(self) -> bool:
        try:
            return bool(self.cap.isOpened())
        except Exception:
            return False

    def start(self):
        if not self.is_opened():
            self.is_running = False
            return self
        self._thread = threading.Thread(target=self.update, daemon=True)
        self._thread.start()
        return self

    def _grab_once(self) -> bool:
        """Read one frame into the shared buffer. Returns True on success."""
        ret, frame = self.cap.read()
        if not ret:
            self._read_failures += 1
            return False
        self._read_failures = 0
        with self.lock:
            self.frame = frame
        return True

    def update(self):
        period = 1.0 / self.target_fps
        while self.is_running and self.is_opened():
            if not self._grab_once():
                if self._read_failures >= 60:   # camera went away -> stop cleanly
                    print("[CameraThreading] too many read failures; stopping")
                    self.is_running = False
                    break
            time.sleep(period)                  # cap grab rate; don't peg a core

    def read(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def stop(self):
        self.is_running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        try:
            self.cap.release()
        except Exception:
            pass
