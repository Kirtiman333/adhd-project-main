"""
Tests for difficulty levels + adaptive progression (src/game_logic/levels.py).

    pytest tests/test_levels.py
    python tests/test_levels.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game_logic.levels import (  # noqa: E402
    Level,
    make_level,
    generate_sequence,
    AdaptiveDifficulty,
    MAX_COLORS,
    MIN_SHOW_FRAMES,
)


def test_make_level_progression():
    l1 = make_level(1)
    l5 = make_level(5)
    assert l5.sequence_length > l1.sequence_length        # longer
    assert l5.show_frames <= l1.show_frames               # faster reveal
    assert l5.flash_frames <= l1.flash_frames
    assert l1.num_colors < l5.num_colors <= MAX_COLORS     # colors actually grow, capped at buttons
    assert l1.num_colors == 3                              # gentle start: 3 colors
    # Floors hold at very high levels.
    assert make_level(999).show_frames >= MIN_SHOW_FRAMES
    assert make_level(999).num_colors <= MAX_COLORS
    # n is clamped to >= 1.
    assert make_level(0).index == 1


def test_generate_sequence_deterministic_and_bounded():
    level = make_level(4)
    a = generate_sequence(level, random.Random(123))
    b = generate_sequence(level, random.Random(123))
    assert a == b                                          # seeded -> reproducible
    assert len(a) == level.sequence_length
    assert all(0 <= c < level.num_colors for c in a)
    # Different seeds generally differ.
    assert generate_sequence(level, random.Random(1)) != a or len(a) <= 1


def test_adaptive_staircase_up_and_down():
    d = AdaptiveDifficulty(start_level=1, advance_after=2)
    assert d.level_index == 1
    d.on_round(True)                 # 1 success, not enough
    assert d.level_index == 1
    d.on_round(True)                 # 2 successes -> level up
    assert d.level_index == 2
    d.on_round(False)                # failure -> level down
    assert d.level_index == 1
    assert d.level.index == 1        # .level reflects index


def test_adaptive_focus_gate_holds_advance():
    d = AdaptiveDifficulty(start_level=1, advance_after=1, focus_gate=40.0)
    d.on_round(True, focus_score=20.0)   # success but low attention -> hold
    assert d.level_index == 1
    d.on_round(True, focus_score=80.0)   # success with good attention -> advance
    assert d.level_index == 2


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
