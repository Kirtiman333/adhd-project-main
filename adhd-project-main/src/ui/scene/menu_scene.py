from src.ui.scene.scene import Scene

class MenuScene(Scene):
    def __init__(self, name):
        super().__init__(name)
        self.create_button(["Play", "Quit", "Calibration", "Logout"])