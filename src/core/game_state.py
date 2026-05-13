from enum import Enum

class GameState(Enum):
    MENU = "Menu"
    PLAYING = "Playing"
    QUIT = "Quit"
    SETTINGS = "Settings"
    CALIBRATE = "Calibrate"
    LOGIN = "Login"