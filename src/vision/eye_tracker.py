"""
Eye tracker: wraps eyetrax's gaze model and turns webcam frames into a smoothed,
screen-space gaze point.

Accuracy-relevant behavior (see also gaze_filter.py / gaze_accuracy.py):
  * predictions come out in the *monitor's* resolution and are scaled into the
    pygame surface space so they line up with what is drawn and aren't dropped;
  * an outlier filter rejects impossible jumps / blink frames;
  * calibration density and the smoother are config-selectable;
  * `validate()` turns held-out (predicted, target) pairs into an accuracy report.

eyetrax and pygame are imported lazily so this module can be imported and the
gaze pipeline unit-tested (with an injected fake estimator/smoother) on a machine
without those heavy dependencies installed.
"""

import os

import numpy as np

from src.config import *
from src.vision.gaze_state import GazeState
from src.vision.gaze_filter import scale_point, GazeFilter
from src.vision.gaze_accuracy import accuracy_metrics


class _IdentitySmoother:
    """Fallback smoother (no-op) used only when eyetrax is unavailable."""
    def step(self, x, y):
        return (x, y)


class EyeTracker:
    def __init__(self, estimator=None, smoother=None, monitor_size=None):
        self.gaze_estimator = estimator if estimator is not None else self._make_estimator()
        self.current_state = GazeState()
        self.has_model = False

        # Model predicts in the physical monitor's resolution; the game/heatmap/
        # scorer all work in the pygame surface space — scale between them.
        self.surface_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self._monitor_size = monitor_size or self._detect_monitor_size()
        self.gaze_filter = GazeFilter(screen=self.surface_size)

        self.smoother = smoother if smoother is not None else self._make_smoother()

    # ---- lazy construction (keeps the module import-safe) -----------------
    @staticmethod
    def _make_estimator():
        from eyetrax.gaze import GazeEstimator
        return GazeEstimator()

    def _detect_monitor_size(self):
        try:
            from eyetrax.utils.screen import get_screen_size
            return get_screen_size()
        except Exception:
            return self.surface_size

    def _make_smoother(self):
        """Select the smoothing filter from config (falls back gracefully)."""
        mode = (GAZE_SMOOTHER or "kalman").lower()
        try:
            from eyetrax.filters import (
                KDESmoother, KalmanEMASmoother, KalmanSmoother, NoSmoother, make_kalman,
            )
            if mode == "none":
                return NoSmoother()
            if mode == "kde":
                return KDESmoother(self.surface_size[0], self.surface_size[1])
            if mode == "kalman_ema":
                return KalmanEMASmoother(make_kalman())
            return KalmanSmoother(make_kalman())
        except Exception as e:
            print(f"[EyeTracker] smoother '{mode}' unavailable ({e}); using identity")
            return _IdentitySmoother()

    # ---- model lifecycle --------------------------------------------------
    def create_model(self, path):
        """Run calibration (density from config) and save. Returns True on success."""
        from eyetrax.calibration import (
            run_5_point_calibration, run_9_point_calibration,
            run_dense_grid_calibration, run_lissajous_calibration,
        )
        calibrations = {
            "5point": run_5_point_calibration,
            "9point": run_9_point_calibration,
            "dense": run_dense_grid_calibration,
            "lissajous": run_lissajous_calibration,
        }
        mode = (CALIBRATION_MODE or "9point").lower()
        calibrate = calibrations.get(mode, run_9_point_calibration)
        try:
            calibrate(self.gaze_estimator)
            self.gaze_estimator.save_model(path)
            self.has_model = os.path.exists(path)
            print(f"[EyeTracker] Created model ({mode}): {path} -> success={self.has_model}")
        except Exception as e:
            self.has_model = False
            print(f"[EyeTracker] create model failed ({path}): {e}")
        return self.has_model

    def load_model(self, path):
        """Load a saved model. Returns True on success."""
        try:
            self.gaze_estimator.load_model(path)
            self.has_model = True
            print(f"[EyeTracker] Loaded model: {path} successfully")
        except Exception as e:
            self.has_model = False
            print(f"[EyeTracker] Load model failed: {e}")
        return self.has_model

    # ---- per-frame inference ---------------------------------------------
    def update(self, frame) -> GazeState:
        if frame is None:
            return self.current_state
        s = self.current_state

        try:
            features, blink_detected = self.gaze_estimator.extract_features(frame)
        except Exception as e:
            # A per-frame tracking hiccup must not take down the 60 FPS game loop.
            print(f"[EyeTracker] feature extraction error: {e}")
            features, blink_detected = None, False

        s.blink_detected = blink_detected  # type: ignore

        gaze_point = None
        if features is not None and not blink_detected:
            try:
                raw = self.gaze_estimator.predict(np.array([features]))[0]
                # monitor-space -> surface-space (mode is validated per setup),
                # then reject outliers / clamp.
                if (GAZE_SCALE_MODE or "scale").lower() == "identity":
                    sx, sy = float(raw[0]), float(raw[1])
                else:
                    sx, sy = scale_point((float(raw[0]), float(raw[1])),
                                         self._monitor_size, self.surface_size)
                smoothed = self.smoother.step(int(sx), int(sy))
                gaze_point = self.gaze_filter.step(smoothed[0], smoothed[1],
                                                   blink=bool(blink_detected))
            except Exception as e:
                print(f"[EyeTracker] prediction error: {e}")
                gaze_point = None

        if gaze_point is not None:
            s.pred_x, s.pred_y = gaze_point
            s.cursor_alpha = min(s.cursor_alpha + CURSOR_STEP, 1.0)
        else:
            s.pred_x = s.pred_y = None
            s.cursor_alpha = max(s.cursor_alpha - CURSOR_STEP, 0.0)

        return s

    # ---- accuracy ---------------------------------------------------------
    def validate(self, pairs):
        """Turn held-out (predicted, target) pixel pairs into an AccuracyReport."""
        return accuracy_metrics(pairs, screen=self.surface_size)

    # ---- rendering --------------------------------------------------------
    def render(self, screen, frame, current_state, font):
        import cv2
        import pygame

        if frame is None:
            return
        frame = cv2.flip(frame, 1)

        if (
            current_state.pred_x is not None
            and current_state.pred_y is not None
            and current_state.cursor_alpha > 0
        ):
            radius = 15
            pygame.draw.circle(
                screen,
                COLORS[4],
                (int(current_state.pred_x), int(current_state.pred_y)),
                radius,
            )

        thumb = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))
        thumb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
        thumb = thumb.swapaxes(0, 1)

        thumb_surface = pygame.surfarray.make_surface(thumb)
        screen.blit(
            thumb_surface,
            (
                screen.get_width() - CAM_WIDTH - MARGIN,
                screen.get_height() - CAM_HEIGHT - MARGIN,
            ),
        )

        blink_txt = "Blinking" if current_state.blink_detected else "Not Blinking"
        blink_clr = (0, 0, 255) if current_state.blink_detected else (0, 255, 0)
        text_surface = font.render(blink_txt, True, blink_clr)
        screen.blit(text_surface, (50, 100))
