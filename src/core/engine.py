import pygame
import random

from src.game_logic.sprites import ColorButton
from src.game_logic.levels import AdaptiveDifficulty, generate_sequence
from src.hardware.controller import SerialColorController, KeyboardColorController
from src.config import *


class GameEngine:
    def __init__(self, event_manager, controller=None):
        self.event_manager = event_manager
        self.timer = 0
        self.player_sequence = []
        self.sequence = []
        self.state = 'SHOWING'
        self.score = 0
        self.wait_timer = 0
        self.shake_amount = 0
        self.show_index = 0

        # Difficulty is now an explicit, adaptive model (src/game_logic/levels.py)
        # instead of a hardcoded length-3 sequence + magic timers.
        self.difficulty = AdaptiveDifficulty(start_level=1)
        self.level = self.difficulty.level
        self._rng = random.Random()
        # Prior session's focus score; gates level advancement (set by GameManager).
        self.session_focus = None

        # Input sources are decoupled behind ColorController (src/hardware/controller.py):
        # serial/Wokwi hardware by default, plus a keyboard fallback (keys 1-4).
        self.controller = controller if controller is not None else self._default_controller()
        self.keyboard = KeyboardColorController()

        self.setup_buttons()
        self.reset_game()

    def _default_controller(self):
        if USE_WOKWI:
            return SerialColorController(WOKWI_URL, baudrate=WOKWI_BAUD)
        return SerialColorController(SERIAL_PORT, baudrate=BAUD_RATE)

    def cleanup(self):
        try:
            self.controller.close()
        except Exception as e:
            print(f"[GameEngine] error closing controller: {e}")

    def reset_game(self):
        self.score = 0
        self.timer = 0
        self.difficulty.reset(start_level=1)
        self.level = self.difficulty.level
        self.sequence = generate_sequence(self.level, self._rng)
        self.player_sequence = []
        self.state = 'SHOWING'
        self.wait_timer = self.level.wait_frames
        self.show_index = 0
        self.shake_amount = 0

    def setup_buttons(self):
        self.buttons = pygame.sprite.Group()
        self.button_list = [
            ColorButton(RED,    0, 390, 110),
            ColorButton(GREEN,  1, 690, 110),
            ColorButton(BLUE,   2, 390, 410),
            ColorButton(YELLOW, 3, 690, 410),
        ]
        for button in self.button_list:
            self.buttons.add(button)

    def _press_color(self, color_id):
        """Register a color press from any input source (mouse / serial / keyboard)."""
        if self.state != 'PLAYING':
            return
        if color_id is None or not (0 <= color_id < len(self.button_list)):
            return
        self.button_list[color_id].flash(10)
        self.player_sequence.append(color_id)
        self._check_step()

    def _handle_events(self, event):
        if self.state == 'PLAYING':
            if event.type == pygame.MOUSEBUTTONDOWN:
                for btn in self.button_list:
                    if btn.rect is not None and btn.rect.collidepoint(event.pos):
                        self._press_color(btn.color_id)
            elif event.type == pygame.KEYDOWN:
                self.keyboard.feed_key(event.key)  # buffered, drained in _update
        elif self.state == 'GAMEOVER' and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.reset_game()
            elif event.key == pygame.K_q:
                self.event_manager.emit("QUIT_GAME")

    def _check_step(self):
        current_idx = len(self.player_sequence) - 1
        if self.player_sequence[current_idx] != self.sequence[current_idx]:
            self.state = 'GAMEOVER'
            self.shake_amount = 20
            self.difficulty.on_round(False)
            self.level = self.difficulty.level
            # Let the GameManager finalize this game's gaze session (save + score + persist).
            self.event_manager.emit("GAME_OVER", {"score": self.score})
        elif len(self.player_sequence) == len(self.sequence):
            self.score += 1
            # Outcome feeds the adaptive staircase; low prior-session focus holds
            # advancement back so difficulty tracks attention, not just memory.
            self.difficulty.on_round(True, focus_score=self.session_focus)
            self.level = self.difficulty.level
            self.sequence = generate_sequence(self.level, self._rng)
            self.state = 'SHOWING'
            self.show_index = 0
            self.timer = 0
            self.wait_timer = self.level.wait_frames

    def _update(self):
        self.buttons.update()

        # Drain every input source through the same color-press path.
        if self.state == 'PLAYING':
            for color_id in (self.controller.poll() + self.keyboard.poll()):
                self._press_color(color_id)
        else:
            # Discard anything buffered outside the player's turn.
            self.controller.poll()
            self.keyboard.poll()

        if self.state == 'SHOWING':
            self.timer += 1
            if self.timer > self.level.show_frames:
                if self.show_index < len(self.sequence):
                    target_id = self.sequence[self.show_index]
                    self.button_list[target_id].flash(self.level.flash_frames)
                    self.show_index += 1
                    self.timer = 0
                else:
                    self.state = 'WAITING'
                    self.timer = 0

        elif self.state == 'WAITING':
            self.wait_timer -= 1
            if self.wait_timer <= 0:
                self.state = 'PLAYING'
                self.player_sequence = []

    def _draw(self, screen, font):
        offset_x = random.randint(-self.shake_amount, self.shake_amount) if self.shake_amount > 0 else 0
        if self.shake_amount > 0:
            self.shake_amount -= 1

        for btn in self.button_list:
            if btn.rect is not None:
                screen.blit(btn.image, (btn.rect.x + offset_x, btn.rect.y))

        if self.state == 'SHOWING':
            status_msg = "REMEMBER THE COLORS!"
        elif self.state == 'WAITING':
            secs = self.wait_timer // FPS + 1
            status_msg = f"STARTING IN: {secs}S"
        elif self.state == 'PLAYING':
            status_msg = "YOUR TURN!"
        elif self.state == 'GAMEOVER':
            # Supportive, growth-oriented copy (the target audience is ADHD/clinical).
            status_msg = f"NICE EFFORT! YOU REACHED ROUND {self.score}.\nR: TRY AGAIN    Q: QUIT"
        else:
            status_msg = ""

        self._blit_centered_lines(screen, font, status_msg, top=30)

        score_surface = font.render(f"SCORE: {self.score}   LEVEL: {self.level.index}", True, WHITE)
        screen.blit(score_surface, (20, 20))

    @staticmethod
    def _blit_centered_lines(screen, font, text, top=30):
        """Render possibly-multi-line text; pygame's font.render ignores '\\n'."""
        line_height = font.get_linesize()
        for i, line in enumerate(text.split("\n")):
            surf = font.render(line, True, WHITE)
            screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, top + i * line_height))
