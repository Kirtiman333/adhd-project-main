import pandas as pd
import cv2
import numpy as np
import os
from datetime import datetime
from src.config import *

class SessionRecorder:
    def __init__(self, user):
        print(f"[SessionRecorder] Initialized session for {user.username} successfully")
        self.user = user
        self.session_dir = user.session_path
        self.heatmap_dir = user.heatmap_path
        self.current_data = []

    def record(self, x, y):
        if x is None or y is None:
            return
        self.current_data.append({
            "timestamp": datetime.now().timestamp(),
            "x": int(x),
            "y": int(y)
        })

    def clear_current_data(self):
        self.current_data.clear()

    def save_session(self):
        if not self.current_data: return None
        
        filename = f"{self.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_session.csv"
        path = os.path.join(self.session_dir, filename)
        
        df = pd.DataFrame(self.current_data)
        df.to_csv(path, index=False)
        self.current_data = [] 
        return path

    def generate_heatmap(self, background_img, csv_path, width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
        if not os.path.exists(csv_path):
            print(f"[SessionRecorder] Do not have session data ({csv_path}) to generate heatmap.")
            return 
        df = pd.read_csv(csv_path)
        accum_map = np.zeros((height, width), dtype=np.float32)

        for _, row in df.iterrows():
            x, y = int(row['x']), int(row['y'])
            if 0 <= x < width and 0 <= y < height:
                accum_map[y, x] += 1

        accum_map = cv2.GaussianBlur(accum_map, (51, 51), 0)
        accum_map = cv2.normalize(accum_map, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX) # type: ignore
        heatmap_img = cv2.applyColorMap(np.uint8(accum_map), cv2.COLORMAP_JET) # type: ignore

        bg = cv2.resize(background_img, (width, height))
        bg = np.uint8(bg)
        overlay = cv2.addWeighted(bg, 0.6, heatmap_img, 0.4, 0) #type: ignore

        out_path = os.path.join(self.heatmap_dir, os.path.basename(csv_path).replace(".csv", ".png"))
        cv2.imwrite(out_path, overlay)
        print(f"[SessionRecorder] Heatmap generated at: {out_path} successfully.")
        return out_path