import json
import os
from datetime import datetime
from pathlib import Path
from src.core.user import User
from src.common.json_utils import JSONUtils

class ProfileManager:
    def __init__(self, data_dir="data"):
        self.json_utils = JSONUtils()
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "users.json")

        self.users_db = self._load_db()
        self._next_id = self._get_starting_id()
    
    def _load_db(self):
        try:
            return self.json_utils.load_json(self.db_path)
        except json.JSONDecodeError:
            return {}

    def _get_starting_id(self):
        if not self.users_db:
            return 1
        
        valid_ids = []
        for uid in self.users_db.keys():
            if str(uid).isdigit(): 
                valid_ids.append(int(uid))
        
        return max(valid_ids) + 1 if valid_ids else 1
    
    def create_user_structure(self, user, base_path=None):
        # Default to this manager's data_dir so folders and users.json never diverge.
        base_path = base_path or self.data_dir
        username = user.username
        userid = user.user_id

        user_dir = f"{username}_{userid}"
        user_path = os.path.join(base_path, user_dir)
        os.makedirs(user_path, exist_ok=True)

        heatmap_dir = f"{username}_heatmap"
        heatmap_path = os.path.join(user_path, heatmap_dir)
        os.makedirs(heatmap_path, exist_ok=True)

        session_dir = f"{username}_session"
        session_path = os.path.join(user_path, session_dir)
        os.makedirs(session_path, exist_ok=True)

        model_dir = f"{username}_model"
        model_path = os.path.join(user_path, model_dir)
        os.makedirs(model_path, exist_ok=True)

        model_file_path = str(
            Path(model_path) / f"{username}_gazemodel.pkl"
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        config = {
            "username": username,
            "userid": userid,
            "user_dir": user_dir,
            "base_path": base_path,

            "session_path": session_path,
            "heatmap_path": heatmap_path,
            "model_path": model_file_path,

            "created_at": timestamp
        }

        self.json_utils.create_json(user_path, "config.json", config)
        print(f"[ProfileManager] created data structure: {user_dir}")

    def create_new_user(self, username, password):
        new_user = User(user_id=self._next_id, name=username, password=password)
        self.create_user_structure(user=new_user)

        config_path = os.path.join(
                self.data_dir,
                f"{new_user.username}_{new_user.user_id}",
                "config.json"
            )

        config = self.json_utils.load_json(config_path)

        if config:
            new_user.set_model_path(config["model_path"])
            new_user.set_session_path(config["session_path"])
            new_user.set_heatmap_path(config["heatmap_path"])

        self._next_id += 1
        self.save_user_profile(new_user)
        return new_user

    def save_user_profile(self, user):
        uid_str = str(user.user_id)
        existing = self.users_db.get(uid_str, {})

        # Preserve the original creation time across saves; only stamp it once.
        created_at = (existing.get("created_at")
                      or existing.get("created at")  # tolerate the old misspelled key
                      or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        # Calibration is considered done once a trained model file exists.
        has_calibration = bool(user.model_path and os.path.exists(str(user.model_path)))

        self.users_db[uid_str] = {
            "name": user.username,
            "password": user.password_hash,
            "stats": user.stats,
            "has_calibration": has_calibration,
            "created_at": created_at,
        }

        self.json_utils.save_json(self.db_path, self.users_db)

    def load_user(self, user_id):
        uid_str = str(user_id)
        if uid_str not in self.users_db:
            return None

        data = self.users_db[uid_str]
        # `password` may be a PBKDF2 hash or, for older profiles, plaintext;
        # User.verify_password handles both.
        user = User(int(uid_str), data.get("name", "Guest"),
                    password_hash=data.get("password"))
        # Merge stored stats over defaults so older profiles missing newer keys still load.
        if isinstance(data.get("stats"), dict):
            user.stats.update(data["stats"])

        user_dir = user.username + "_" + uid_str
        config_path = os.path.join(self.data_dir, user_dir, "config.json")
        config = self.json_utils.load_json(config_path)
        if config:
            user.set_session_path(config.get("session_path"))
            user.set_heatmap_path(config.get("heatmap_path"))
            user.set_model_path(config.get("model_path"))

        return user

    def get_all_users(self):
        return {uid: info["name"] for uid, info in self.users_db.items()}
    
    def find_user_by_name(self, name):
        for uid, info in self.users_db.items():
            if info['name'] == name:
                return self.load_user(uid)
        return None