import pygame_gui
from src.core.game_state import GameState
from src.ui.scene.hud_scene import HudScene
from src.ui.scene.menu_scene import MenuScene
from src.ui.scene.login_scene import LoginScene
from src.ui.scene.stats_scene import StatsScene
from src.config import *

class UIManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.menu = MenuScene(MENU_THEME)
        self.hub = HudScene(HUD_THEME)
        self.login = LoginScene(LOGIN_THEME)
        self.stats = StatsScene(MENU_THEME)
        self.managers = {
            GameState.LOGIN: self.login.manager,
            GameState.MENU: self.menu.manager,
            GameState.PLAYING: self.hub.manager,
            GameState.STATS: self.stats.manager,
        }

        self.current_state = GameState.LOGIN
        self.current_manager = self.managers[self.current_state]
        self.setup_ui()
        self.setup_events()

    def setup_events(self):
        self.event_manager.subscribe(
            "MODEL_STATUS_CHANGED",
            self.on_model_status_changed
        )
        self.event_manager.subscribe("LOGIN_FAILED", self.on_login_failed)

    def on_login_failed(self, data):
        self.login.message.show(data.get("reason", "Login failed"))

    def show_stats(self, report, scored=None):
        self.stats.show_report(report, scored)

    def on_model_status_changed(self, data):
        self.model_found = data.get("has_model", False)

        if self.model_found:
            self.calibrate_button.hide()
        else:
            self.calibrate_button.show()
   

    def setup_ui(self):
        # Login 
        self.login_button = self.login.buttons[0]
        self.login_quit_button = self.login.buttons[1]
        self.username_box = self.login.username_box
        self.password_box = self.login.password_box
        self.username_label = self.login.username_label
        self.password_label = self.login.password_label

        # Menu
        self.play_button = self.menu.buttons[0]
        self.quit_button = self.menu.buttons[1]
        self.calibrate_button = self.menu.buttons[2]
        self.logout_button = self.menu.buttons[3]
        self.progress_button = self.menu.buttons[4]

        # Playing
        self.back_button = self.hub.buttons[0]

        # Stats
        self.stats_back_button = self.stats.back_button

    def switch_state(self, new_state):
        # Only switch to states that actually have a registered manager; this
        # avoids a KeyError on QUIT/CALIBRATE/SETTINGS or any future state.
        if new_state == self.current_state or new_state not in self.managers:
            return
        self.current_state = new_state
        self.current_manager = self.managers[new_state]

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if self.current_state == GameState.LOGIN:
                if event.ui_element == self.login_button:
                    self.login.message.clear()
                    username = self.username_box.get_text()
                    password = self.password_box.get_text()
                    self.event_manager.emit(
                        "LOGIN_REQUEST",
                        {
                            "username": username,
                            "password": password
                        }
                    )
                elif event.ui_element == self.login_quit_button:
                    self.event_manager.emit("QUIT_GAME")
            elif self.current_state == GameState.MENU:
                if event.ui_element == self.play_button:
                    self.event_manager.emit("START_GAME")
                elif event.ui_element == self.quit_button:
                    self.event_manager.emit("QUIT_GAME")
                elif event.ui_element == self.logout_button:
                    self.event_manager.emit("BACK_TO_LOGIN")
                elif event.ui_element == self.calibrate_button:
                    if self.calibrate_button.visible:
                        self.event_manager.emit("START_CALIBRATION")
                elif event.ui_element == self.progress_button:
                    self.event_manager.emit("SHOW_STATS")
            elif self.current_state == GameState.PLAYING:
                if event.ui_element == self.back_button:
                    self.event_manager.emit("BACK_TO_MENU")
            elif self.current_state == GameState.STATS:
                if event.ui_element == self.stats_back_button:
                    self.event_manager.emit("BACK_TO_MENU")

        self.current_manager.process_events(event)

    def update(self, deltaTime):
        self.current_manager.update(deltaTime)

    def render(self, screen):
        self.current_manager.draw_ui(screen)