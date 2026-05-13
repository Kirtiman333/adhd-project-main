import pygame
from src.config import *

class ColorButton(pygame.sprite.Sprite):
    def __init__(self, color, color_id, x, y):
        super().__init__()
        self.color_id = color_id
        self.base_color = color
        self.base_size = (200, 200)
        self.flash_size = (220, 220)

        self.image = pygame.Surface(self.base_size)
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.is_flashing = False
        self.flash_timer = 0    

    def flash(self, duration=30):
        self.is_flashing = True
        self.flash_timer = duration

        bright_color = tuple(min(255, c + 100) for c in self.base_color)
        self.image = pygame.Surface(self.flash_size)
        self.image.fill(bright_color)

        pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 10)
        old_center = self.rect.center # type: ignore
        self.rect = self.image.get_rect(center=old_center)

    def update(self):
        if self.is_flashing:
            self.flash_timer -= 1
            if self.flash_timer <= 0:
                self.is_flashing = False

                self.image = pygame.Surface(self.base_size)
                self.image.fill(self.base_color)
                old_center = self.rect.center # type: ignore
                self.rect = self.image.get_rect(center=old_center)