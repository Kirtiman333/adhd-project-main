from pathlib import Path

# Anchor every path to the project root so they resolve on any OS and regardless
# of the current working directory (config.py lives at <root>/src/config.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED    = (255, 50, 50)
GREEN  = (50, 255, 50)
BLUE   = (50, 50, 255)
YELLOW = (255, 255, 50)
ORANGE = (255, 165, 0)

COLORS = [RED, GREEN, BLUE, YELLOW, ORANGE]
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
TEXT_BOX_WIDTH = 300
TEXT_BOX_HEIGHT = 40
LABEL_WIDTH = 200
LABEL_HEIGHT = 30

SERIAL_PORT = 'COM3' 
BAUD_RATE = 9600

MENU_THEME = str(PROJECT_ROOT / "assets" / "themes" / "menu_theme.json")
HUD_THEME = str(PROJECT_ROOT / "assets" / "themes" / "hud_theme.json")
LOGIN_THEME = str(PROJECT_ROOT / "assets" / "themes" / "login_theme.json")

# wokwi server path for simulator testing before use hardware
WOKWI_SERVER = str(PROJECT_ROOT / "wokwi_simulate_server" / "wokwigw.exe")

# wokwi serial gateway (used by SerialColorController)
WOKWI_URL = "rfc2217://localhost:4000"
WOKWI_BAUD = 115200
USE_WOKWI = True  # False -> use SERIAL_PORT/BAUD_RATE (real Arduino) instead

# --- Gameplay / difficulty ---
# Single source of truth for the playable colors (button order == color_id).
COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]
COLOR_IDS = {name: i for i, name in enumerate(COLOR_NAMES)}

START_SEQUENCE_LENGTH = 3     # length of the first round's sequence
SHOW_FRAMES = 30              # frames between revealing each color while SHOWING
FLASH_FRAMES = 20            # how long each revealed color flashes
WAIT_FRAMES = 3 * FPS        # countdown before the player's turn

# eye_tracker
CAMERA_ID = 0
CAM_FPS = 30                 # cap the capture grab rate (avoids pegging a CPU core)
CAM_WIDTH = 200
CAM_HEIGHT = 120
BODER = 2
MARGIN = 20
CURSOR_STEP = 0.05

# --- Gaze accuracy / calibration ---
# How model predictions (in the calibration monitor's pixels) map to the game
# surface. "scale" assumes the game fills the monitor (predictions are scaled
# monitor->surface). "identity" assumes the prediction is already in surface
# space (e.g. a borderless window at the monitor origin). VALIDATE THIS ON THE
# REAL SETUP with the webcam: if the gaze cursor is offset/shrunk, switch modes.
GAZE_SCALE_MODE = "scale"   # "scale" | "identity"

# Calibration density: "5point" | "9point" | "dense" | "lissajous" (more points = better fit)
CALIBRATION_MODE = "9point"
# Smoother: "kalman" | "kalman_ema" | "kde" | "none"
GAZE_SMOOTHER = "kalman"
# Reject gaze jumps larger than this fraction of the screen diagonal as outliers.
GAZE_OUTLIER_JUMP_RATIO = 0.6
# A calibration is considered good if mean validation error is within this many px.
CALIBRATION_MAX_ERROR_PX = 120

#user profile
MODEL_PATH = str(PROJECT_ROOT / "data" / "models" / "gaze_model.pkl")