from datetime import datetime

from src.common.security import hash_password, verify_password


class User:
    def __init__(self, user_id, name="Guest", password="", password_hash=None):
        self.user_id = user_id
        self.username = name
        # `password_hash` is the stored credential (a PBKDF2 hash, or a legacy
        # plaintext value loaded from an old profile). Passing `password=` hashes
        # a fresh plaintext password for a brand-new account.
        if password_hash is not None:
            self.password_hash = password_hash
        elif password:
            self.password_hash = hash_password(password)
        else:
            self.password_hash = ""

        self.stats = {
            "total_games": 0,
            "high_score": 0,
            "last_played": "N/A",
            "last_focus_score": None,
            "best_focus_score": None,
        }
        self.model_path = None
        self.heatmap_path = None
        self.session_path = None

    # ---- credentials -----------------------------------------------------
    def set_password(self, raw):
        self.password_hash = hash_password(raw)

    def verify_password(self, raw):
        return verify_password(raw, self.password_hash)

    # ---- progress --------------------------------------------------------
    def record_game(self, score, focus_score=None, when=None):
        """Update lifetime stats after a finished game. Pure, no I/O."""
        self.stats["total_games"] = self.stats.get("total_games", 0) + 1
        self.stats["high_score"] = max(self.stats.get("high_score", 0) or 0, score)
        self.stats["last_played"] = when or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if focus_score is not None:
            self.stats["last_focus_score"] = focus_score
            prev_best = self.stats.get("best_focus_score") or 0
            self.stats["best_focus_score"] = max(prev_best, focus_score)
        return self.stats

    # ---- paths -----------------------------------------------------------
    def set_model_path(self, path):
        self.model_path = path

    def set_heatmap_path(self, path):
        self.heatmap_path = path

    def set_session_path(self, path):
        self.session_path = path
