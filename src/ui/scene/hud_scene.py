from src.ui.scene.scene import Scene

class HudScene(Scene):
    def __init__(self, name):
        super().__init__(name)
        self.create_button(["Back"], rect=(1180,10,100))
