
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

MENU_THEME = r"assets\themes\menu_theme.json"
HUD_THEME = r"assets\themes\hud_theme.json"
LOGIN_THEME = r"assets\themes\login_theme.json"

# wokwi server path for simulator testing before use hardware
WOKWI_SERVER = r"wokwi_simulate_server\wokwigw.exe" 

# eye_tracker
CAM_WIDTH = 200
CAM_HEIGHT = 120
BODER = 2
MARGIN = 20
CURSOR_STEP = 0.05

#user profile
MODEL_PATH = r"data\models\gaze_model.pkl"