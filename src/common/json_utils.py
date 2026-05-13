import json
import os

class JSONUtils:
    def __init__(self):
        pass

    def create_json(self, path, json_filename, data):
        profile_path = os.path.join(path, json_filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load_json(self, path):
        if not os.path.exists(path):
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    def save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)