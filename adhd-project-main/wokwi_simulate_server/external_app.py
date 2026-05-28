import subprocess

class ExternalApp:
    def __init__(self, path):
        self.path = path
        self.process = None

    def start(self):
        if self.process is None or self.process.poll() is not None:
            self.process = subprocess.Popen(
                self.path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()