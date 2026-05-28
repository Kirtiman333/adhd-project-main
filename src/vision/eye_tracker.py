import cv2
import pygame
import numpy as np

from src.config import *

from eyetrax.calibration import (
    run_5_point_calibration,
    run_9_point_calibration,
    run_dense_grid_calibration,
    run_lissajous_calibration,
)
from eyetrax.cli import parse_common_args
from eyetrax.filters import (
    KDESmoother,
    KalmanEMASmoother,
    KalmanSmoother,
    NoSmoother,
    make_kalman,
)
from eyetrax.gaze import GazeEstimator
from eyetrax.utils.draw import draw_cursor, make_thumbnail
from eyetrax.utils.screen import get_screen_size

from src.config import *
from src.vision.gaze_state import GazeState


class EyeTracker:
    def __init__(self):
        self.gaze_estimator = GazeEstimator()
        self.current_state = GazeState()

        # user can add more background instead of black screen
        self.filter()

    def create_model(self, path):
        try:
            run_5_point_calibration(self.gaze_estimator)
            self.gaze_estimator.save_model(path)
            print(f"[EyeTracker] Created model: {path} successfully")
        except Exception as e:
            print(f"[EyeTracker] \033[91mError:\033[0m create model failed: {path}", end="\n")

    def load_model(self, path):
        try:
            self.gaze_estimator.load_model(path)
            print(f"[EyeTracker] Loaded model: {path} successfully")
        except Exception as e:
            print(f"[EyeTracker] \033[91mError:\033[0m Load model failed: {e}", end="\n")

    # should add optional button
    def filter(self):
        self.kalman = make_kalman()
        self.smoother = KalmanSmoother(self.kalman)

    def update(self, frame) -> GazeState: 
        if frame is None:
            return self.current_state
        s = self.current_state
        features, blink_detected = self.gaze_estimator.extract_features(frame)  
        s.blink_detected = blink_detected  # type: ignore

        if features is not None and not blink_detected:
            gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
            x, y = map(int, gaze_point)
            s.pred_x, s.pred_y = self.smoother.step(x, y) # type: ignore
            s.cursor_alpha = min(s.cursor_alpha + CURSOR_STEP, 1.0)
        else:
            s.pred_x = s.pred_y = None
            s.cursor_alpha = max(s.cursor_alpha - CURSOR_STEP, 0.0)

        return s

    def render(self, screen, frame, current_state, font):
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
                radius
            )    

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

        blink_txt = "Blinking" if current_state.blink_detected else "Not Blinking"
        blink_clr = (0, 0, 255) if current_state.blink_detected else (0, 255, 0)

        text_surface = font.render(blink_txt, True, blink_clr)
        screen.blit(text_surface, (50, 100))


