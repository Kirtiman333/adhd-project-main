"""
Reusable, theme-aware UI widgets built on pygame_gui.

Shared building blocks used across scenes (e.g. the login feedback banner and the
stats dashboard) so scenes don't construct labels/inputs by hand.
"""

import pygame
import pygame_gui


def make_label(manager, text, x, y, w=400, h=30, object_id=None):
    kwargs = {}
    if object_id is not None:
        kwargs["object_id"] = object_id
    return pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((x, y), (w, h)),
        text=text,
        manager=manager,
        **kwargs,
    )


class FormMessage:
    """An inline status/error banner for a scene (e.g. login feedback)."""

    def __init__(self, manager, x, y, w=400, h=30):
        self.label = make_label(manager, "", x, y, w, h)

    def show(self, text):
        self.label.set_text(text)
        self.label.show()

    def clear(self):
        self.label.set_text("")
        self.label.hide()


class MetricList:
    """A rebuildable vertical list of text rows (the stats dashboard body)."""

    def __init__(self, manager, x, y, w=560, row_h=30, spacing=6):
        self.manager = manager
        self.x, self.y, self.w = x, y, w
        self.row_h, self.spacing = row_h, spacing
        self.rows = []

    def set_rows(self, lines):
        for r in self.rows:
            r.kill()
        self.rows = []
        for i, text in enumerate(lines):
            y = self.y + i * (self.row_h + self.spacing)
            self.rows.append(make_label(self.manager, text, self.x, y, self.w, self.row_h))


def focus_bar(score, width=10):
    """A tiny ASCII bar for a 0-100 score (renders fine in any pygame_gui label)."""
    filled = max(0, min(width, int(round(score / 100 * width))))
    return "[" + "#" * filled + "." * (width - filled) + "]"
