import cv2
import threading

class CameraThreading:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.frame = None
        self.lock = threading.Lock()
        self.cap = cv2.VideoCapture(self.camera_id)
        self.is_running = True

    def start(self):
        t = threading.Thread(target=self.update, daemon=True)
        t.start()
        return self
    
    def update(self):
        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue

            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.is_running = False
        self.cap.release()