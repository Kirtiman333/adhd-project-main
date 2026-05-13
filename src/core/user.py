class User:
    def __init__(self, user_id, name="Guest", password=""):
        self.user_id = user_id
        self.username = name
        self.password = password
        self.stats = {
            "total_games": 0, 
            "high_score": 0, 
            "last_played": "N/A"
        }
        self.model_path = None
        self.heatmap_path = None
        self.session_path = None

    def set_model_path(self, path):
        self.model_path = path

    def set_heatmap_path(self, path):
        self.heatmap_path = path

    def set_session_path(self, path):
        self.session_path = path