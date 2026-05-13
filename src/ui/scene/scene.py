import pygame_gui
import pygame
from src.config import *


class Scene:
    def __init__(self, name=None):
        self.manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), theme_path=name)
        self.buttons = []
    
    def create_button(self, texts, rect=(540, 200, BUTTON_WIDTH, BUTTON_HEIGHT), spacing=70):
        if rect.__len__() == 1:
            rect = (540, rect[0], BUTTON_WIDTH, BUTTON_HEIGHT)
        elif rect.__len__() == 2:
            rect = (rect[0], rect[1], BUTTON_WIDTH, BUTTON_HEIGHT)
        elif rect.__len__() == 3:
            rect = (rect[0], rect[1], rect[2], BUTTON_HEIGHT)
        for i, text in enumerate(texts):
            button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((rect[0], rect[1] + spacing*i), (rect[2], rect[3])),
                text=text,
                manager=self.manager
            )
            self.buttons.append(button)

    def create_text_box(self, rect=(540, 200, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT)):
        if rect.__len__() == 1:
            rect = (540, rect[0], TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT)
        elif rect.__len__() == 2:
            rect = (rect[0], rect[1], TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT)
        elif rect.__len__() == 3:
            rect = (rect[0], rect[1], rect[2], TEXT_BOX_HEIGHT)
        text_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((rect[0], rect[1]), (rect[2], rect[3])),
            manager=self.manager
        )
        return text_box

    def create_label(self, text="", rect=(400, 200, LABEL_WIDTH, LABEL_HEIGHT)):
        if rect.__len__() == 1:
            rect = (400, rect[0], LABEL_WIDTH, LABEL_HEIGHT)
        elif rect.__len__() == 2:
            rect = (rect[0], rect[1], LABEL_WIDTH, LABEL_HEIGHT)
        elif rect.__len__() == 3:
            rect = (rect[0], rect[1], rect[2], LABEL_HEIGHT)
        label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((rect[0], rect[1]), (rect[2], rect[3])),
            text=text,
            manager=self.manager
        )
        return label

