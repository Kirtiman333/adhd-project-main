"""
Difficulty levels and adaptive progression for the color-sequence game.

Models difficulty as an explicit, testable structure instead of hardcoded
sequence lengths and timing constants:

  * `Level` — the parameters of one difficulty step (sequence length, how many
    colors are in play, and the frame timings that pace the round).
  * `make_level(n)` — derive level N from the config defaults: longer sequences,
    faster reveals, and (eventually) more colors as N grows.
  * `generate_sequence(level, rng)` — a deterministic, seedable sequence builder.
  * `AdaptiveDifficulty` — a "staircase" controller: step the level up after a
    few clean rounds, ease it down after a slip, and let a low attention
    (focus) score hold difficulty back so the player isn't pushed past their
    current sustained-attention capacity.

Pure standard library + config — no pygame — so it is fully unit-testable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from src.config import (
    COLOR_NAMES,
    START_SEQUENCE_LENGTH,
    SHOW_FRAMES,
    FLASH_FRAMES,
    WAIT_FRAMES,
)

MAX_COLORS = len(COLOR_NAMES)       # playable colors (button count)
MIN_SHOW_FRAMES = 8                 # don't reveal faster than this
MIN_FLASH_FRAMES = 6


@dataclass(frozen=True)
class Level:
    index: int
    sequence_length: int
    num_colors: int
    show_frames: int
    flash_frames: int
    wait_frames: int


def make_level(n: int) -> Level:
    """Build level `n` (1-based). Higher n = longer sequence, faster reveal, more colors."""
    n = max(1, int(n))
    sequence_length = START_SEQUENCE_LENGTH + (n - 1)
    # Start with 3 colors and add one every 2 levels, capped at the button count
    # (gentle onboarding, then the full color set).
    num_colors = min(MAX_COLORS, 3 + (n - 1) // 2)
    show_frames = max(MIN_SHOW_FRAMES, SHOW_FRAMES - (n - 1) * 2)
    flash_frames = max(MIN_FLASH_FRAMES, FLASH_FRAMES - (n - 1) * 2)
    return Level(
        index=n,
        sequence_length=sequence_length,
        num_colors=num_colors,
        show_frames=show_frames,
        flash_frames=flash_frames,
        wait_frames=WAIT_FRAMES,
    )


def generate_sequence(level: Level, rng: Optional[random.Random] = None) -> list:
    """Return a list of color_ids of length `level.sequence_length`.

    Pass a seeded `random.Random` for deterministic sequences (tests / replays).
    """
    rng = rng or random.Random()
    top = max(1, min(level.num_colors, MAX_COLORS))
    return [rng.randrange(top) for _ in range(level.sequence_length)]


class AdaptiveDifficulty:
    """Staircase difficulty controller driven by round outcomes and focus score.

    * `advance_after` consecutive successes -> level up.
    * any failure -> level down by one (never below 1) and reset the streak.
    * if a focus score is supplied and is below `focus_gate`, hold the level
      (don't advance) even on success — attention, not just memory, gates progress.
    """

    def __init__(self, start_level: int = 1, advance_after: int = 2,
                 max_level: int = 50, focus_gate: float = 40.0):
        self.level_index = max(1, start_level)
        self.advance_after = max(1, advance_after)
        self.max_level = max_level
        self.focus_gate = focus_gate
        self._streak = 0

    @property
    def level(self) -> Level:
        return make_level(self.level_index)

    def on_round(self, success: bool, focus_score: Optional[float] = None) -> Level:
        """Update difficulty after a round and return the (possibly new) Level."""
        if success:
            self._streak += 1
            attention_ok = focus_score is None or focus_score >= self.focus_gate
            if self._streak >= self.advance_after and attention_ok:
                self.level_index = min(self.max_level, self.level_index + 1)
                self._streak = 0
        else:
            self._streak = 0
            self.level_index = max(1, self.level_index - 1)
        return self.level

    def reset(self, start_level: int = 1) -> None:
        self.level_index = max(1, start_level)
        self._streak = 0
