"""
Color-input controllers — decouple the game engine from the input source.

Keeps pyserial out of the engine (which would otherwise be impossible to
construct or test without a live Wokwi/Arduino endpoint) behind one small
protocol:

    poll() -> list[int]   # color_ids pressed since the last poll
    close()               # release any resources

with several implementations:

    * NullController       — never produces input (headless / tests)
    * KeyboardColorController — maps keys to color_ids (no-hardware fallback)
    * SerialColorController   — reads color names from a serial/Wokwi stream

pyserial and pygame are imported lazily inside the implementations that need
them, so importing this module (and unit-testing the decode/mapping/keyboard
logic) never requires those packages to be installed.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Dict, List, Optional

from src.config import COLOR_IDS


def decode_color_line(line: str, name_to_id: Optional[Dict[str, int]] = None) -> Optional[int]:
    """Map a serial line like 'RED' (any case / surrounding whitespace) to a color_id.

    Returns None for unknown / empty tokens. Pure and unit-testable.
    """
    if not line:
        return None
    name_to_id = name_to_id or COLOR_IDS
    return name_to_id.get(line.strip().upper())


class ColorController:
    """Base controller. Subclasses push color_ids; callers drain them via poll()."""

    def __init__(self):
        self._buffer: List[int] = []

    def _push(self, color_id: Optional[int]) -> None:
        if color_id is not None:
            self._buffer.append(int(color_id))

    def poll(self) -> List[int]:
        """Return and clear the color_ids accumulated since the last poll."""
        out, self._buffer = self._buffer, []
        return out

    def close(self) -> None:
        pass


class NullController(ColorController):
    """Produces no input. Lets the engine run/headless-test without hardware."""


class KeyboardColorController(ColorController):
    """Keyboard fallback: feed pygame KEYDOWN keycodes via feed_key().

    `key_map` maps keycode -> color_id. If omitted, a default 1/2/3/4 + R/G/B/Y
    map is built lazily from pygame (so the import only happens when actually
    used at runtime, not at module import / test time).
    """

    def __init__(self, key_map: Optional[Dict[int, int]] = None):
        super().__init__()
        self.key_map = key_map if key_map is not None else self._default_key_map()

    @staticmethod
    def _default_key_map() -> Dict[int, int]:
        # Number keys 1-4 only — letter keys (R/Q) are reserved for restart/quit.
        try:
            import pygame
        except Exception:
            return {}
        return {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}

    def feed_key(self, keycode: int) -> Optional[int]:
        """Translate a keycode to a color_id and buffer it. Returns the id (or None)."""
        color_id = self.key_map.get(keycode)
        self._push(color_id)
        return color_id


class SerialColorController(ColorController):
    """Read color names from a serial / Wokwi rfc2217 stream on a background thread.

    Construction failures (no endpoint, pyserial missing) are non-fatal: the
    controller simply yields no input, so the game still runs with mouse/keyboard.
    """

    def __init__(self, url: str, baudrate: int = 115200,
                 name_to_id: Optional[Dict[str, int]] = None, timeout: float = 0.01):
        super().__init__()
        self.name_to_id = name_to_id or COLOR_IDS
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._running = False
        self._ser = None
        self._thread: Optional[threading.Thread] = None
        try:
            import serial  # lazy: only needed for real serial input
            self._ser = serial.serial_for_url(url, baudrate=baudrate, timeout=timeout)
            self._running = True
            self._thread = threading.Thread(target=self._reader, daemon=True)
            self._thread.start()
            print(f"[SerialColorController] connected to {url}")
        except Exception as e:
            print(f"[SerialColorController] disabled (no serial input): {e}")
            self._ser = None

    def _reader(self) -> None:
        while self._ser and self._running:
            try:
                if self._ser.in_waiting > 0:
                    line = self._ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self._queue.put(line)
                else:
                    time.sleep(0.001)
            except Exception as e:
                # Don't spin/spam on a dead port — back off and stop cleanly.
                print(f"[SerialColorController] read error, stopping reader: {e}")
                self._running = False
                break

    def poll(self) -> List[int]:
        while not self._queue.empty():
            self._push(decode_color_line(self._queue.get(), self.name_to_id))
        return super().poll()

    def close(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
