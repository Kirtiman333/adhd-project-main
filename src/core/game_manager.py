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
            self.session_recorder.record(predicted_gaze_x, predicted_gaze_y)

    def render_gaze_cursor(self):
        self.eye_tracker.render(self.screen, self.current_frame, self.current_state, self.font)

    def generate_heatmap(self):
        path = self.session_recorder.save_session()
        bg = pygame.surfarray.array3d(self.screen)
        bg = np.transpose(bg, (1, 0, 2))  # quan trọng nhất

        bg = np.uint8(bg)
        self.session_recorder.generate_heatmap(bg, path)

    # event subsribers setup
    def setup_event_subscribers(self):
        self.event_manager.subscribe("LOGIN_REQUEST", self.validate_login)
        self.event_manager.subscribe("START_CALIBRATION", self.start_calibration)
        self.event_manager.subscribe("BACK_TO_MENU", self.back_to_menu)
        self.event_manager.subscribe("QUIT_GAME", self.quit_game)
        self.event_manager.subscribe("START_GAME", self.start_game)
        self.event_manager.subscribe("BACK_TO_LOGIN", self.back_to_login)
        self.event_manager.subscribe("MODEL_STATUS_CHANGED", self.on_model_status_changed)

    # event handlers
    def validate_login(self, data):
        username = data["username"].strip()
        password = data["password"].strip()

        if not username:
            print(f"[GameManager] User '{username}' attempted to log in with empty username.")
            return
        user = self.profile_manager.find_user_by_name(username)
        if user:
            if user.password != password:
                print(f"[GameManager] User '{username}' attempted to log in with incorrect password.")
                return
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
            print("[GameManager] no model → calibration required")

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

            if self.game_state == GameState.PLAYING and not self.has_camera:
                self.setup_camera()
                self.has_camera = True

            if self.current_user and self.eye_tracker is None:
                self.eye_tracker = EyeTracker()

            self.engine._handle_events(event)

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
        self.generate_heatmap()
        pygame.quit()
        sys.exit()
