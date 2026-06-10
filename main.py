import sys

# Make console output robust on Windows (default cp1252 console crashes on any
# non-ASCII char, e.g. arrows or accented log text). UTF-8 with replace is safe.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.core.game_manager import GameManager

if __name__ == "__main__":
    print("[GameManager] game starting ....")
    game = GameManager()
    game.run()
