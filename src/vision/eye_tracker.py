import cv2
import pygame
import numpy as np

from eyetrax.calibration import (
    run_5_point_calibration,
    run_9_point_calibration,
    run_lissajous_calibration,
)

from eyetrax.gaze import GazeEstimator
from eyetrax.filters import make_kalman, KalmanSmoother

from src.config import *
from src.vision.gaze_state import GazeState


class EyeTracker:
    def __init__(self):
        self.gaze_estimator = GazeEstimator()
        self.current_state = GazeState()

        self._init_filter()

    # -----------------------------
    # MODEL
    # -----------------------------
    def create_model(self, path):
        try:
            run_5_point_calibration(self.gaze_estimator)
            self.gaze_estimator.save_model(path)
            print(f"[EyeTracker] Model created: {path}")
        except Exception as e:
            print(f"[EyeTracker] create_model error: {e}")

    def load_model(self, path):
        try:
            self.gaze_estimator.load_model(path)
            print(f"[EyeTracker] Model loaded: {path}")
        except Exception as e:
            print(f"[EyeTracker] load_model error: {e}")

    # -----------------------------
    # FILTER
    # -----------------------------
    def _init_filter(self):
        self.kalman = make_kalman()
        self.smoother = KalmanSmoother(self.kalman)

    # -----------------------------
    # UPDATE
    # -----------------------------
    def update(self, frame) -> GazeState:
        if frame is None:
            return self.current_state

        s = self.current_state

        try:
            features, blink_detected = self.gaze_estimator.extract_features(frame)
        except Exception:
            return s

        s.blink_detected = blink_detected  # type: ignore

        if features is not None and not blink_detected:
            try:
                gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
                x, y = map(int, gaze_point)

                s.pred_x, s.pred_y = self.smoother.step(x, y)  # type: ignore
                s.cursor_alpha = min(s.cursor_alpha + CURSOR_STEP, 1.0)

            except Exception:
                s.pred_x = s.pred_y = None
        else:
            s.pred_x = s.pred_y = None
            s.cursor_alpha = max(s.cursor_alpha - CURSOR_STEP, 0.0)

        return s

    # -----------------------------
    # RENDER
    # -----------------------------
    def render(self, screen, frame, current_state, font):
        if frame is None:
            return

        frame = cv2.flip(frame, 1)

        # cursor
        if (
            current_state.pred_x is not None
            and current_state.pred_y is not None
            and current_state.cursor_alpha > 0
        ):
            pygame.draw.circle(
                screen,
                COLORS[4],
                (int(current_state.pred_x), int(current_state.pred_y)),
                15
            )

        # camera preview
        try:
            thumb = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))
            thumb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
            thumb = thumb.swapaxes(0, 1)

            thumb_surface = pygame.surfarray.make_surface(thumb)

            screen.blit(
                thumb_surface,
                (
                    screen.get_width() - CAM_WIDTH - MARGIN,
                    screen.get_height() - CAM_HEIGHT - MARGIN
                )
            )
        except Exception:
            pass

        # blink text
        blink_txt = "Blinking" if current_state.blink_detected else "Not Blinking"
        blink_clr = (0, 0, 255) if current_state.blink_detected else (0, 255, 0)

        text_surface = font.render(blink_txt, True, blink_clr)
        screen.blit(text_surface, (50, 100))