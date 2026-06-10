import os

import numpy as np
import pygame
import sys

from src.common.event_manager import EventManager
from src.core.game_state import GameState
from src.ui.ui_manager import UIManager
from src.core.engine import GameEngine
from src.vision.camera_threading import CameraThreading
from src.vision.eye_tracker import EyeTracker
from wokwi_simulate_server.external_app import ExternalApp
from src.core.profile_manager import ProfileManager
from src.core.session_recorder import SessionRecorder
from src.common.security import needs_rehash
from src.config import *

class GameManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
        pygame.display.set_caption("ADHD Tracker - Demo Version")
        self.font = pygame.font.SysFont("Arial", 32)
        self.big_font = pygame.font.SysFont("Arial", 64)
        self.clock = pygame.time.Clock()
        self.is_running = True
        self.game_state = GameState.LOGIN
        self.has_camera = False
        self.eye_tracker = None
        self.current_user = None
        self.session_finalized = True  # no active session until a game starts

        # initialize event manager
        self.event_manager = EventManager()

        # initialize managers
        self.ui = UIManager(self.event_manager)   
        self.engine = GameEngine(self.event_manager)
        self.wokwi_server = ExternalApp(WOKWI_SERVER)
        self.profile_manager = ProfileManager()
        self.setup_event_subscribers()
        # self.wokwi_server.start()

    # eye tracker and sesstion recorder setups
    def setup_eye_tracker(self, current_user):
        self.eye_tracker = EyeTracker()
        self.session_recorder = SessionRecorder(current_user) 

    def setup_camera(self):
        self.camera = CameraThreading().start()
        self.current_frame = None
        self.current_state = None
    
    # camera and eye tracker updates
    def update_camera(self):
        self.current_frame = self.camera.read()
        if self.current_frame is not None:
            self.current_state = self.eye_tracker.update(self.current_frame)
            predicted_gaze_x, predicted_gaze_y = self.current_state.pred_x, self.current_state.pred_y
            # Stop recording once the round is over so post-game-over frames don't
            # leak into (and double-count) the next finalize.
            if self.engine.state != 'GAMEOVER':
                self.session_recorder.record(predicted_gaze_x, predicted_gaze_y)

    def render_gaze_cursor(self):
        self.eye_tracker.render(self.screen, self.current_frame, self.current_state, self.font)

    def finalize_session(self):
        """Save + score the current gaze session, persist stats, render the heatmap.

        Safe to call from any state: no-ops if nothing was recorded or the
        recorder/screen aren't ready. This is where raw gaze becomes a focus
        score that lands in the user's profile.
        """
        recorder = getattr(self, "session_recorder", None)
        if recorder is None or self.session_finalized:
            return

        path = recorder.save_session()
        if not path:
            return  # nothing recorded this session

        # Mark finalized up-front so the quit path can't double-count this game.
        self.session_finalized = True
        metrics = recorder.score_session(path)
        focus_score = metrics.focus_score if metrics else None

        if self.current_user is not None:
            self.current_user.record_game(self.engine.score, focus_score=focus_score)
            self.profile_manager.save_user_profile(self.current_user)
            if metrics:
                print(f"[GameManager] Session focus score: {metrics.focus_score} ({metrics.label})")

        # Heatmap over whatever gameplay frame is currently on screen.
        try:
            bg = np.uint8(np.transpose(pygame.surfarray.array3d(self.screen), (1, 0, 2)))
            recorder.generate_heatmap(bg, path)
        except Exception as e:
            print(f"[GameManager] heatmap generation skipped: {e}")

    def on_game_over(self, data=None):
        """End-of-game hook: finalize the session so score/focus are saved per game."""
        self.finalize_session()

    def on_show_stats(self, data=None):
        """Build the user's focus-progress report and show the dashboard."""
        from src.core.progress import build_progress
        session_dir = self.current_user.session_path if self.current_user else None
        report, scored = build_progress(session_dir)
        self.ui.show_stats(report, scored)
        self.game_state = GameState.STATS
        self.ui.switch_state(GameState.STATS)

    # event subsribers setup
    def setup_event_subscribers(self):
        self.event_manager.subscribe("LOGIN_REQUEST", self.validate_login)
        self.event_manager.subscribe("START_CALIBRATION", self.start_calibration)
        self.event_manager.subscribe("BACK_TO_MENU", self.back_to_menu)
        self.event_manager.subscribe("QUIT_GAME", self.quit_game)
        self.event_manager.subscribe("START_GAME", self.start_game)
        self.event_manager.subscribe("BACK_TO_LOGIN", self.back_to_login)
        self.event_manager.subscribe("MODEL_STATUS_CHANGED", self.on_model_status_changed)
        self.event_manager.subscribe("GAME_OVER", self.on_game_over)
        self.event_manager.subscribe("SHOW_STATS", self.on_show_stats)

    def _login_failed(self, reason):
        print(f"[GameManager] login failed: {reason}")
        self.event_manager.emit("LOGIN_FAILED", {"reason": reason})

    # event handlers
    def validate_login(self, data):
        username = data["username"].strip()
        password = data["password"].strip()

        if not username:
            self._login_failed("Please enter a username.")
            return
        if not password:
            self._login_failed("Please enter a password.")
            return
        user = self.profile_manager.find_user_by_name(username)
        if user:
            if not user.verify_password(password):
                self._login_failed("Incorrect password.")
                return
            # Transparently upgrade legacy plaintext / weaker hashes after a good login.
            if needs_rehash(user.password_hash):
                user.set_password(password)
                self.profile_manager.save_user_profile(user)
            self.current_user = user
            print(f"[GameManager] User '{username}' logged in successfully.")
        else:
            new_user = self.profile_manager.create_new_user(
                username=username,
                password=password
            )
            self.current_user = new_user
            print(f"[GameManager] New user created: {new_user.username}")
        
        self.game_state = GameState.MENU
        self.ui.switch_state(GameState.MENU)
        self.event_manager.emit("MODEL_STATUS_CHANGED", {
            "has_model": os.path.exists(str(self.current_user.model_path)),
            "model_path": str(self.current_user.model_path)
        })

    def on_model_status_changed(self, data):
        has_model = data["has_model"]
        if has_model:
            self.setup_eye_tracker(self.current_user)

            if self.current_user and self.current_user.model_path:
                self.eye_tracker.load_model(self.current_user.model_path)
        else:
            print("[GameManager] no model -> calibration required")

    def start_calibration(self):
        print(f"[GameManager] switch to calibrate")
        self.eye_tracker.create_model(self.current_user.model_path)
        self.game_state = GameState.MENU
        self.ui.switch_state(self.game_state)
        self.event_manager.emit("MODEL_STATUS_CHANGED", {
            "has_model": True,
            "model_path": str(self.current_user.model_path)
        })

    def back_to_menu(self):
        print(f"[GameManager] switch to menu")
        self.game_state = GameState.MENU
        self.ui.switch_state(self.game_state)

    def quit_game(self):
        print(f"[GameManager] quit game")
        self.is_running = False

    def start_game(self):
        print(f"[GameManager] switch to playing")
        self.game_state = GameState.PLAYING
        self.ui.switch_state(self.game_state)
        self.engine.reset_game()
        # Attention-gated difficulty: carry the prior session's focus into this game.
        if self.current_user is not None:
            self.engine.session_focus = self.current_user.stats.get("last_focus_score")
        # A fresh session begins — allow it to be finalized exactly once.
        self.session_finalized = False
        if getattr(self, "session_recorder", None) is not None:
            self.session_recorder.clear_current_data()

    def back_to_login(self):
        print(f"[GameManager] switch to login")
        self.game_state = GameState.LOGIN
        self.ui.switch_state(self.game_state)
    #//

    # main game logic
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
                return
            
            # handle events for each manager
            self.ui.handle_event(event)

            # Set up the camera once, only when we actually have a trained tracker.
            if (self.game_state == GameState.PLAYING and not self.has_camera
                    and self.eye_tracker is not None):
                self.setup_camera()
                self.has_camera = True

            self.engine._handle_events(event)

    def _gaze_ready(self):
        """True only when the whole gaze pipeline is set up (camera + tracker + recorder)."""
        return (self.has_camera
                and self.eye_tracker is not None
                and getattr(self, "camera", None) is not None
                and getattr(self, "session_recorder", None) is not None)

    def update(self, deltaTime):
        self.ui.update(deltaTime)
        match self.game_state:
            case GameState.LOGIN:
                pass
            case GameState.MENU:
                pass
            case GameState.CALIBRATE:
                pass
            case GameState.PLAYING:
                self.engine._update()
                if self._gaze_ready():
                    self.update_camera()
            case GameState.QUIT:
                pass

    def render(self):
        self.screen.fill((0, 0, 0))
        match self.game_state:
            case GameState.LOGIN:
                pass
            case GameState.PLAYING:
                self.engine._draw(self.screen, self.font)
                if self._gaze_ready():
                    self.render_gaze_cursor()
            case GameState.MENU:
                pass
            case GameState.QUIT:
                pass
        self.ui.render(self.screen)
        pygame.display.update()

    def run(self):
        while self.is_running:
            deltaTime = self.clock.tick(FPS)/1000.0
            self.handle_events()
            self.update(deltaTime)
            self.render()
        if self.has_camera:
            self.camera.stop()
        self.wokwi_server.stop()
        self.engine.cleanup()
        if not self.session_finalized:   # don't re-finalize a game already saved on GAME_OVER
            self.finalize_session()
        pygame.quit()
        sys.exit()
