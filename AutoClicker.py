import time
import threading
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, KeyCode

# --- SETTINGS ---
TOGGLE_KEY = KeyCode(char='f') # Press 'f' to toggle ON/OFF
DELAY = 0.1                    # 10 clicks per second (SAFE)
# ----------------

mouse = Controller()
running = False

def clicker():
    while True:
        if running:
            mouse.click(Button.left, 0.1)
            time.sleep(DELAY) # CRITICAL: This prevents the browser crash
        time.sleep(0.01) # Lowers CPU usage

def on_press(key):
    global running
    if key == TOGGLE_KEY:
        running = not running
        print(f"Clicker: {'ON' if running else 'OFF'}")

# Start the clicking thread so it doesn't block the listener
threading.Thread(target=clicker, daemon=True).start()

print(f"Ready! Hover over your game and press '{TOGGLE_KEY.char}' to toggle.")
with Listener(on_press=on_press) as listener:
    listener.join()
