"""
Per-user progress aggregation.

Turns a user's recorded gaze sessions (the *_session.csv files SessionRecorder
writes under their session folder) into a focus-score trend the in-game stats
dashboard can render. Pure standard library + the attention scorer — no pygame —
so the data layer behind the dashboard is unit-testable on its own.
"""

from __future__ import annotations

import glob
import os
from typing import List, Optional, Tuple

from src.config import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game_logic.scoring import AttentionScorer, SessionMetrics, ProgressReport


def find_user_session_csvs(session_dir: Optional[str]) -> List[str]:
    """Return the user's session CSVs in chronological order (filenames embed the timestamp)."""
    if not session_dir or not os.path.isdir(session_dir):
        return []
    return sorted(glob.glob(os.path.join(session_dir, "*_session.csv")))


def build_progress(session_dir: Optional[str],
                   screen: Tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT),
                   limit: Optional[int] = None):
    """Score every session under `session_dir` and summarize the trend.

    Returns (ProgressReport, [(label, SessionMetrics), ...]).
    `limit` keeps only the most recent N sessions (e.g. for a compact dashboard).
    """
    scorer = AttentionScorer(screen=screen)
    csvs = find_user_session_csvs(session_dir)
    if limit:
        csvs = csvs[-limit:]

    scored: List[Tuple[str, SessionMetrics]] = []
    for path in csvs:
        metrics = scorer.score_csv(path)
        label = _session_label(path)
        scored.append((label, metrics))

    report = scorer.summarize_progress(scored)
    return report, scored


def _session_label(path: str) -> str:
    """Short human label from a '<user>_<YYYYmmdd>_<HHMMSS>_session.csv' filename."""
    name = os.path.basename(path).replace("_session.csv", "")
    parts = name.split("_")
    if len(parts) >= 2:
        return f"{parts[-2]} {parts[-1]}"   # date time
    return name
