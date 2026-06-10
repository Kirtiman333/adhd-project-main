"""
Tests for ProfileManager + User: hashed credentials, persisted stats, and
robust create_at preservation.

    pytest tests/test_profile_manager.py
    python tests/test_profile_manager.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.profile_manager import ProfileManager  # noqa: E402


def _pm(tmp):
    return ProfileManager(data_dir=tmp)


def test_password_is_hashed_not_stored_plaintext():
    with tempfile.TemporaryDirectory() as tmp:
        pm = _pm(tmp)
        pm.create_new_user("alice", "s3cret-pw")

        raw = Path(pm.db_path).read_text(encoding="utf-8")
        assert "s3cret-pw" not in raw, "plaintext password leaked into users.json"

        # Fresh manager reloads from disk and verifies the password.
        pm2 = _pm(tmp)
        u = pm2.find_user_by_name("alice")
        assert u is not None
        assert u.verify_password("s3cret-pw") is True
        assert u.verify_password("wrong") is False


def test_stats_persist_via_record_game():
    with tempfile.TemporaryDirectory() as tmp:
        pm = _pm(tmp)
        u = pm.create_new_user("bob", "pw")

        u.record_game(score=7, focus_score=82.5)
        pm.save_user_profile(u)

        u2 = _pm(tmp).find_user_by_name("bob")
        assert u2.stats["total_games"] == 1
        assert u2.stats["high_score"] == 7
        assert u2.stats["last_focus_score"] == 82.5
        assert u2.stats["best_focus_score"] == 82.5

        # A lower-scoring game keeps the high score / best focus.
        u2.record_game(score=3, focus_score=50)
        _pm(tmp).save_user_profile(u2)
        u3 = _pm(tmp).find_user_by_name("bob")
        assert u3.stats["total_games"] == 2
        assert u3.stats["high_score"] == 7
        assert u3.stats["best_focus_score"] == 82.5
        assert u3.stats["last_focus_score"] == 50


def test_created_at_preserved_across_saves():
    with tempfile.TemporaryDirectory() as tmp:
        pm = _pm(tmp)
        u = pm.create_new_user("carol", "pw")
        first = json.loads(Path(pm.db_path).read_text(encoding="utf-8"))
        created = first[str(u.user_id)]["created_at"]

        u.record_game(score=1)
        pm.save_user_profile(u)
        again = json.loads(Path(pm.db_path).read_text(encoding="utf-8"))
        assert again[str(u.user_id)]["created_at"] == created


def test_legacy_plaintext_profile_loads_and_verifies():
    with tempfile.TemporaryDirectory() as tmp:
        pm = _pm(tmp)
        # Simulate an old DB row that stored the password in plaintext.
        pm.users_db["1"] = {
            "name": "dave",
            "password": "oldplain",
            "stats": {"total_games": 4, "high_score": 9},
            "created_at": "2020-01-01 00:00:00",
        }
        pm.json_utils.save_json(pm.db_path, pm.users_db)

        u = _pm(tmp).find_user_by_name("dave")
        assert u.verify_password("oldplain") is True
        # Older row missing the newer stat keys still loads with defaults.
        assert u.stats["high_score"] == 9
        assert "best_focus_score" in u.stats


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
