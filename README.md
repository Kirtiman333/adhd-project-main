# ADHD Attention Trainer

A focus-training game that pairs a **Simon-style color-memory game** with **webcam
eye-tracking**. While you play, the app tracks your gaze, turns it into attention
metrics (a 0–100 *focus score*), and shows your progress over time. Color input
can come from the mouse, the keyboard (keys 1–4), or a physical Arduino color-button
rig (real hardware or the Wokwi simulator over serial).

## How it works

```
LOGIN ──> MENU ──> PLAYING ──> (GAME OVER) ──> finalize session
            │                                    │
            ├─ Calibration (eye-tracking model)  ├─ gaze CSV  ──> focus score ──> profile
            └─ Progress (focus-score dashboard)  └─ heatmap
```

- **Vision** (`src/vision/`): threaded webcam capture → `eyetrax` gaze model →
  smoothed, screen-scaled, outlier-filtered gaze point.
- **Game** (`src/core/engine.py`, `src/game_logic/`): the color-sequence game with
  adaptive difficulty (`levels.py`) and pluggable input (`src/hardware/controller.py`).
- **Scoring** (`src/game_logic/scoring.py`): turns a session's gaze stream into
  attention metrics; `src/core/progress.py` aggregates them into a trend.

## Setup

Requires **Python 3.10+** (and a webcam for the eye-tracking features).

```bash
python -m venv .venv
. .venv/Scripts/activate     # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
python main.py                              # launch the game (needs pygame + webcam)
```

No hardware? You can still see the analysis pipeline:

```bash
python tools/attention_report.py --demo     # attention report on synthetic gaze
python tools/accuracy_benchmark.py          # estimated gaze-accuracy before/after the fixes
```

Real recorded sessions live under `data/<user>_<id>/<user>_session/*_session.csv`;
score them with `python tools/attention_report.py --user <name>`.

## Tests

Pure-logic modules are unit-tested and run with **or without** pytest:

```bash
pytest tests/                # all tests
python tests/test_scoring.py # any single file, no pytest needed
```

## Data layout

```
data/
  users.json                         # profiles (passwords are PBKDF2-hashed)
  <user>_<id>/
    config.json
    <user>_session/  *_session.csv   # recorded gaze (timestamp,x,y)
    <user>_heatmap/  *.png
    <user>_model/    *_gazemodel.pkl # calibrated eye-tracking model
```

`data/` is git-ignored — profiles and gaze data never leave your machine.

## Hardware / simulator (optional)

The Arduino color buttons can run on real hardware (`SERIAL_PORT`/`BAUD_RATE` in
`src/config.py`) or the Wokwi simulator gateway (`WOKWI_URL`). Set `USE_WOKWI` in
config to choose. See `arduino/` for the firmware and `wokwi_simulate_server/` for
the gateway.
