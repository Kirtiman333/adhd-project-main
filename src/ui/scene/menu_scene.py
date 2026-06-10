from src.ui.scene.scene import Scene

class MenuScene(Scene):
    def __init__(self, name):
        super().__init__(name)
        # Order matters: UIManager.setup_ui indexes these by position.
        self.create_button(["Play", "Quit", "Calibration", "Logout", "Progress"])