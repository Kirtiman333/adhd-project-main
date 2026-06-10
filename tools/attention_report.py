"""
Attention report — turns recorded gaze sessions into a readable focus report.

Usage:
    python tools/attention_report.py --demo              # synthetic demo, no hardware needed
    python tools/attention_report.py --csv path/to.csv   # score one real session CSV
    python tools/attention_report.py --user alice         # score all of a user's sessions under data/

With no arguments it auto-detects: if recorded sessions exist under data/, it
reports on them; otherwise it falls back to the synthetic demo so the pipeline
is always demonstrable on a fresh checkout.
"""

from __future__ import annotations

import argparse
import glob
import os
import random
import sys
from pathlib import Path
from typing import List, Tuple

# Allow running directly from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.game_logic.scoring import AttentionScorer, SessionMetrics  # noqa: E402

DATA_DIR = "data"


# --------------------------------------------------------------------------- #
# Synthetic sessions — let the report run with zero setup, and show the metric
# responding correctly to genuinely focused vs. genuinely distracted play.
# --------------------------------------------------------------------------- #
def _synthetic_session(kind: str, seed: int, screen=(1280, 720), hz=20, seconds=30):
    """Generate a believable gaze stream. `kind` in {focused, distracted}."""
    rng = random.Random(seed)
    w, h = screen
    n = hz * seconds
    t0 = 1_700_000_000.0  # fixed epoch base (deterministic, no wall-clock)
    pts: List[Tuple[float, float, float]] = []
    cx, cy = w / 2, h / 2
    for i in range(n):
        t = t0 + i / hz
        if kind == "focused":
            # Long fixations near a target, with occasional small re-fixations.
            if i % 120 == 0:  # drift to a new nearby target every ~6s
                cx = _clamp(cx + rng.uniform(-120, 120), 60, w - 60)
                cy = _clamp(cy + rng.uniform(-90, 90), 60, h - 60)
            x = cx + rng.gauss(0, 12)
            y = cy + rng.gauss(0, 12)
        else:
            # Frequent large jumps all over the screen = distractible gaze.
            if i % 6 == 0:
                cx = rng.uniform(60, w - 60)
                cy = rng.uniform(60, h - 60)
            x = cx + rng.gauss(0, 45)
            y = cy + rng.gauss(0, 45)
        pts.append((t, _clamp(x, 0, w), _clamp(y, 0, h)))
    return pts


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --------------------------------------------------------------------------- #
# Real session discovery
# --------------------------------------------------------------------------- #
def _find_user_sessions(user: str, data_dir: str = DATA_DIR) -> List[str]:
    """Find a user's *_session.csv files, newest patterns last (chronological)."""
    pattern = os.path.join(data_dir, f"{user}_*", f"{user}_session", "*_session.csv")
    files = glob.glob(pattern)
    # Filenames embed YYYYmmdd_HHMMSS, so a lexical sort is chronological.
    return sorted(files)


def _find_any_sessions(data_dir: str = DATA_DIR) -> List[str]:
    return sorted(glob.glob(os.path.join(data_dir, "*", "*_session", "*_session.csv")))


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _bar(score: float, width: int = 24) -> str:
    filled = int(round(width * _clamp(score, 0, 100) / 100))
    return "#" * filled + "." * (width - filled)


def _print_session(title: str, m: SessionMetrics) -> None:
    print(f"\n  {title}")
    if m.sample_count < 2:
        print(f"    (skipped — {m.note})")
        return
    print(f"    Focus score        {m.focus_score:5.1f}/100  [{_bar(m.focus_score)}]  {m.label}")
    print(f"    Sustained attention {m.focus_ratio * 100:4.0f}% of session in fixations")
    print(f"    Longest focus       {m.longest_focus_s:5.1f}s   (peak sustained attention)")
    print(f"    Fixations           {m.fixation_count:4d}      mean {m.mean_fixation_s:.2f}s each")
    print(f"    Distraction events  {m.distraction_events:4d}      ({m.distraction_rate_hz:.2f}/s)")
    print(f"    Gaze dispersion     {m.dispersion_px:5.0f}px   (lower = more concentrated)")
    print(f"    Session length      {m.duration_s:5.1f}s   {m.sample_count} samples @ {m.sampling_hz:.0f} Hz")


def _print_progress(report) -> None:
    print("\n" + "=" * 60)
    print("  PROGRESS ACROSS SESSIONS")
    print("=" * 60)
    if report.session_count == 0:
        print("  No usable sessions yet.")
        return
    for label, score in report.per_session:
        print(f"    {label:<22} {score:5.1f}  [{_bar(score, 18)}]")
    arrow = {"Improving": "^", "Declining": "v", "Stable": "="}.get(report.trend, ".")
    sign = "+" if report.delta >= 0 else ""
    print("-" * 60)
    print(f"    Trend: {report.trend} {arrow}   "
          f"first {report.first_score:.1f} -> last {report.last_score:.1f} "
          f"({sign}{report.delta})")
    print(f"    Best {report.best_score:.1f}   mean {report.mean_score:.1f}   "
          f"over {report.session_count} sessions")


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
def run_demo(scorer: AttentionScorer) -> None:
    print("=" * 60)
    print("  ATTENTION REPORT  (synthetic demo - no hardware needed)")
    print("=" * 60)
    print("  Two simulated players, scored by the same engine that would")
    print("  score a real recorded session:")

    scored = []
    # A short improvement arc: distracted -> mixed -> focused.
    runs = [
        ("Session 1 (distracted)", "distracted", 1),
        ("Session 2 (improving)", "focused", 7),
        ("Session 3 (focused)", "focused", 3),
    ]
    for title, kind, seed in runs:
        m = scorer.score(_synthetic_session(kind, seed))
        _print_session(title, m)
        scored.append((title.split(" (")[0], m))

    _print_progress(scorer.summarize_progress(scored))
    print("\n  (Plug a real data/<user>/<user>_session/*.csv in with --csv or --user")
    print("   to run this on actual recorded gaze instead.)")


def run_csv(scorer: AttentionScorer, path: str) -> None:
    print("=" * 60)
    print(f"  ATTENTION REPORT  -  {path}")
    print("=" * 60)
    _print_session(os.path.basename(path), scorer.score_csv(path))


def run_user(scorer: AttentionScorer, user: str, data_dir: str) -> None:
    files = _find_user_sessions(user, data_dir)
    print("=" * 60)
    print(f"  ATTENTION REPORT  -  user '{user}'  ({len(files)} session(s))")
    print("=" * 60)
    if not files:
        print(f"  No sessions found under {data_dir}/{user}_*/{user}_session/.")
        return
    scored = []
    for path in files:
        m = scorer.score_csv(path)
        _print_session(os.path.basename(path), m)
        scored.append((os.path.basename(path)[:22], m))
    _print_progress(scorer.summarize_progress(scored))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Attention report for recorded gaze sessions.")
    ap.add_argument("--demo", action="store_true", help="run on synthetic data (no hardware)")
    ap.add_argument("--csv", help="score a single session CSV")
    ap.add_argument("--user", help="score all sessions for a user under data/")
    ap.add_argument("--data-dir", default=DATA_DIR, help="data directory (default: data)")
    args = ap.parse_args(argv)

    scorer = AttentionScorer()

    if args.csv:
        run_csv(scorer, args.csv)
    elif args.user:
        run_user(scorer, args.user, args.data_dir)
    elif args.demo:
        run_demo(scorer)
    elif _find_any_sessions(args.data_dir):
        # Auto: real data present -> report on the most recent user's sessions.
        latest = _find_any_sessions(args.data_dir)[-1]
        user_dir = Path(latest).parts[-3]          # data/<user>_<id>/...
        user = user_dir.rsplit("_", 1)[0]
        run_user(scorer, user, args.data_dir)
    else:
        run_demo(scorer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
