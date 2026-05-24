import sys
import time
import threading

class RainbowSpinner:
    def __init__(self, message="🤖 Lab Sync Pensando..."):
        self.message = message
        self.is_running = False
        self.thread = None
        
        # Braille spinner frames
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
        # Rainbow colors using ANSI escape codes
        self.colors = [
            '\033[91m', # Red
            '\033[93m', # Yellow
            '\033[92m', # Green
            '\033[96m', # Cyan
            '\033[94m', # Blue
            '\033[95m'  # Magenta
        ]
        self.reset_color = '\033[0m'

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join()
            
        # Clear the line completely
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()

    def _spin(self):
        frame_idx = 0
        color_idx = 0
        while self.is_running:
            frame = self.frames[frame_idx]
            color = self.colors[color_idx]
            
            # Print frame with color, then message
            sys.stdout.write(f"\r{color}{frame} {self.message}{self.reset_color}")
            sys.stdout.flush()
            
            frame_idx = (frame_idx + 1) % len(self.frames)
            # Change color every few frames to make it look smooth
            if frame_idx % 2 == 0:
                color_idx = (color_idx + 1) % len(self.colors)
                
            time.sleep(0.1)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
