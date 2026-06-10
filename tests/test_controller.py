"""
Tests for color-input controllers (src/hardware/controller.py).

    pytest tests/test_controller.py
    python tests/test_controller.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hardware.controller import (  # noqa: E402
    decode_color_line,
    NullController,
    KeyboardColorController,
    SerialColorController,
)


def test_decode_color_line():
    assert decode_color_line("RED") == 0
    assert decode_color_line("  green ") == 1
    assert decode_color_line("Blue") == 2
    assert decode_color_line("yellow") == 3
    assert decode_color_line("PURPLE") is None
    assert decode_color_line("") is None
    assert decode_color_line(None) is None


def test_null_controller():
    c = NullController()
    assert c.poll() == []
    c.close()  # no-op, must not raise


def test_keyboard_controller_maps_and_drains():
    # explicit key_map of arbitrary ints -> no pygame needed
    c = KeyboardColorController(key_map={97: 0, 98: 1, 99: 2})
    assert c.feed_key(97) == 0
    assert c.feed_key(99) == 2
    assert c.feed_key(123) is None          # unmapped key -> not buffered
    assert c.poll() == [0, 2]
    assert c.poll() == []                   # poll clears the buffer


def test_serial_controller_degrades_gracefully_without_serial():
    # pyserial isn't required to import this module; a bad/unavailable endpoint
    # must not raise and must simply produce no input.
    c = SerialColorController("rfc2217://localhost:65000", baudrate=115200)
    assert c.poll() == []
    c.close()


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
