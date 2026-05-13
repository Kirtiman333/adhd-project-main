from src.config import *
from src.ui.scene.scene import Scene


class LoginScene(Scene):
    def __init__(self, name=None):
        super().__init__(name)
        self.create_button(texts=["Login", "Quit"], rect=(250,))
        self.username_box = self.create_text_box(rect=(150,))
        self.password_box = self.create_text_box(rect=(200,))
        self.username_label = self.create_label(text="Username:", rect=(155,))
        self.password_label = self.create_label(text="Password:", rect=(205,))
        self.password_box.set_text_hidden(True)