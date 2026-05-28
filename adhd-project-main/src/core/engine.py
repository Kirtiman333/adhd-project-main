import pygame
import random
import serial
import threading
import time
import queue
from src.core.game_state import GameState
from src.game_logic.sprites import ColorButton  
from src.config import *


class GameEngine:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.timer = 0
        self.player_sequence = []
        self.sequence = []
        self.state = 'SHOWING'
        self.score = 0
        self.wait_timer = 0
        self.shake_amount = 0
        self.show_index = 0
        self.setup_buttons()
        self.reset_game()

        # Đọc dữ liệu từ Wokwi server, tạo một thread mới chỉ đọc :))) 
        self.serial_queue = queue.Queue()
        self.serial_running = False

        url = "rfc2217://localhost:4000"
        try:
            self.ser = serial.serial_for_url(url, baudrate=115200, timeout=0.01)
            self.serial_running = True
            threading.Thread(target=self._serial_thread, daemon=True).start()
            print(f"[GameEngine] Connected to {url} successfully.")
        except Exception as e:
            print(f"[GameEngine] {e}")
            self.ser = None

    def _serial_thread(self):
        while self.ser and self.serial_running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    self.serial_queue.put(line)
                else:
                    time.sleep(0.001)
            except Exception as e:
                print(f"[GameEngine] Serial error: {e}")

    def cleanup(self):
        self.serial_running = False
        if self.ser:
            try:
                self.ser.close()
                print(f"[GameEngine] Serial connection closed successfully.")
            except Exception as e:
                print(f"[GameEngine] \033[91m[GameEngine] Error:\033[0m cannot close serial connection", end="")
                

    def reset_game(self):
        self.score = 0
        self.timer = 0
        self.sequence = [random.randint(0, 3) for _ in range(3)]
        self.player_sequence = []
        self.state = 'SHOWING'
        self.wait_timer = 3 * FPS
        self.show_index = 0
        self.shake_amount = 0

    def setup_buttons(self):
        self.buttons = pygame.sprite.Group()
        self.button_list = [
             ColorButton(RED,    0, 390, 110),
            ColorButton(GREEN,  1, 690, 110),

            ColorButton(BLUE,   2, 390, 410),
            ColorButton(YELLOW, 3, 690, 410)
        ]
        for button in self.button_list:
            self.buttons.add(button)

    def _handle_events(self, event):
        # Handle game events, now tested with mouse clicks
        if self.state == 'PLAYING' and event.type == pygame.MOUSEBUTTONDOWN:
            for btn in self.button_list:
                if btn.rect != None and btn.rect.collidepoint(event.pos): 
                    btn.flash(10)
                    self.player_sequence.append(btn.color_id)
                    self._check_step()
            
        if self.state == 'GAMEOVER' and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: self.reset_game()
            if event.key == pygame.K_q: self.event_manager.emit("QUIT_GAME")

    def _check_step(self):
        current_idx = len(self.player_sequence) - 1
        if self.player_sequence[current_idx] != self.sequence[current_idx]:
            self.state = 'GAMEOVER'
            self.shake_amount = 20
        elif len(self.player_sequence) == len(self.sequence):
            self.score += 1
            self.sequence = [random.randint(0, 3) for _ in range(3)]
            self.state = 'SHOWING'
            self.show_index = 0
            self.wait_timer = 5 * FPS

    # def isLosed(self):
    #     return self.state == 'GAMEOVER'

    def _update(self):
        self.buttons.update()

        # Đọc data từ wokwi server 
        while not self.serial_queue.empty():
            line = self.serial_queue.get()
            try:
                if line in ['RED', 'GREEN', 'BLUE', 'YELLOW'] and self.state == 'PLAYING':
                    if line == 'RED': color_id = 0
                    elif line == 'GREEN': color_id = 1  
                    elif line == 'BLUE': color_id = 2
                    elif line == 'YELLOW': color_id = 3
                    print(f"[GameEngine] Received data: {line}")
                    self.button_list[color_id].flash(10)
                    self.player_sequence.append(color_id)
                    self._check_step()
            except Exception as e:
                print(f"[GameEngine] \033[91mError:\033[0m {e}", end="")

        if self.state == 'SHOWING':
            self.timer += 1
            if self.timer > 30: 
                if self.show_index < len(self.sequence):
                    target_id = self.sequence[self.show_index]
                    self.button_list[target_id].flash(20)
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
        if self.shake_amount > 0: self.shake_amount -= 1

        for btn in self.button_list:
            if btn.rect != None:
                screen.blit(btn.image, (btn.rect.x + offset_x, btn.rect.y)) 

        status_msg = ""
        if self.state == 'SHOWING': status_msg = "REMEMBER THE COLORS!"
        elif self.state == 'WAITING': 
            secs = self.wait_timer // FPS + 1
            status_msg = f"STARTING IN: {secs}S"
        elif self.state == 'PLAYING': status_msg = "YOUR TURN!"
        elif self.state == 'GAMEOVER': status_msg = "YOU'RE STUPID!!!\nR: AGAIN | Q: QUIT"

        msg_surface = font.render(status_msg, True, WHITE)
        screen.blit(msg_surface, (SCREEN_WIDTH//2 - msg_surface.get_width()//2, 30))
        
        # Vẽ điểm
        score_surface = font.render(f"SCORE: {self.score}", True, WHITE)
        screen.blit(score_surface, (20, 20))
