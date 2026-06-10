"""
Headless smoke test - actually constructs and drives the real app (no window,
no webcam) to catch import / construction / wiring errors that unit tests can't.

Runs pygame under the dummy video/audio drivers, builds GameManager (which builds
every scene, the engine, profile manager, etc.), and exercises the real event
flows: login (create + re-login + wrong password), the stats dashboard, starting
a game, a forced game-over, and the switch_state guard. Profile data is written
to a throwaway temp dir.

    python tools/smoke_test.py
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

# Must be set before pygame is imported (transitively, via GameManager).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Keep profile data out of the repo.
os.chdir(tempfile.mkdtemp(prefix="adhd_smoke_"))

_results = []


def check(name, fn):
    try:
        fn()
        _results.append(True)
        print(f"  PASS  {name}")
    except Exception as e:  # noqa: BLE001
        _results.append(False)
        print(f"  FAIL  {name}: {e!r}")
        traceback.print_exc()


from src.core.game_manager import GameManager  # noqa: E402
from src.core.game_state import GameState      # noqa: E402

state = {}


def construct():
    gm = GameManager()
    assert gm.game_state == GameState.LOGIN
    state["gm"] = gm


def login_creates_user():
    gm = state["gm"]
    gm.event_manager.emit("LOGIN_REQUEST", {"username": "smoke", "password": "pw123"})
    assert gm.current_user is not None, "no user after login"
    assert gm.game_state == GameState.MENU, f"expected MENU, got {gm.game_state}"


def relogin_correct_and_wrong_password():
    gm = state["gm"]
    failures = []
    gm.event_manager.subscribe("LOGIN_FAILED", lambda d: failures.append(d["reason"]))
    # wrong password for the existing user -> LOGIN_FAILED, no login
    gm.current_user = None
    gm.event_manager.emit("LOGIN_REQUEST", {"username": "smoke", "password": "WRONG"})
    assert failures, "wrong password did not emit LOGIN_FAILED"
    assert gm.current_user is None
    # correct password -> logs in (verifies the live PBKDF2 hash round-trip)
    gm.event_manager.emit("LOGIN_REQUEST", {"username": "smoke", "password": "pw123"})
    assert gm.current_user is not None, "correct password failed to log in"


def empty_username_feedback():
    gm = state["gm"]
    fired = []
    gm.event_manager.subscribe("LOGIN_FAILED", lambda d: fired.append(d))
    gm.event_manager.emit("LOGIN_REQUEST", {"username": "  ", "password": "x"})
    assert fired, "empty username did not produce LOGIN_FAILED"


def show_stats_dashboard():
    gm = state["gm"]
    gm.event_manager.emit("SHOW_STATS")
    assert gm.game_state == GameState.STATS, f"expected STATS, got {gm.game_state}"
    gm.event_manager.emit("BACK_TO_MENU")
    assert gm.game_state == GameState.MENU


def switch_state_guard():
    gm = state["gm"]
    before = gm.ui.current_state
    gm.ui.switch_state(GameState.SETTINGS)   # not registered -> must not raise
    assert gm.ui.current_state == before


def start_game_and_loop():
    gm = state["gm"]
    gm.event_manager.emit("START_GAME")
    assert gm.game_state == GameState.PLAYING
    assert len(gm.engine.sequence) == gm.engine.level.sequence_length
    # Drive the real loop body (update + render) without the blocking while-loop.
    for _ in range(90):
        gm.update(1 / 60)
        gm.render()


def forced_game_over():
    gm = state["gm"]
    eng = gm.engine
    eng.state = "PLAYING"
    eng.sequence = [0]
    eng.player_sequence = []
    eng._press_color(1)   # wrong -> GAMEOVER + GAME_OVER event + finalize (no recorder -> safe)
    assert eng.state == "GAMEOVER"
    gm.render()           # game-over screen renders (supportive multi-line text)


def cleanup():
    gm = state["gm"]
    gm.engine.cleanup()
    import pygame
    pygame.quit()


print("=" * 64)
print("  HEADLESS SMOKE TEST (SDL dummy driver, no webcam)")
print("=" * 64)
check("construct GameManager (pygame + pygame_gui + all scenes + engine)", construct)
check("login creates a new user and switches to MENU", login_creates_user)
check("re-login: wrong password rejected, correct password accepted", relogin_correct_and_wrong_password)
check("empty username shows on-screen feedback (LOGIN_FAILED)", empty_username_feedback)
check("Progress dashboard opens and returns (StatsScene)", show_stats_dashboard)
check("switch_state ignores unregistered states (no KeyError)", switch_state_guard)
check("START_GAME + 90 frames of update/render (engine + UI)", start_game_and_loop)
check("forced game-over finalizes safely and renders", forced_game_over)
check("clean shutdown", cleanup)

passed = sum(_results)
print("-" * 64)
print(f"  {passed}/{len(_results)} smoke checks passed")
sys.exit(0 if passed == len(_results) else 1)
