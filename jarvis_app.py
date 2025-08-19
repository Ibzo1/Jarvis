import webview
import sys
import threading
from pynput import keyboard
from jarvis_core import Jarvis

# --- The Same API Class ---
class Api:
    def __init__(self):
        self.jarvis = Jarvis()
        self.window = None

    def process_command(self, command):
        if command:
            return self.jarvis.get_response(command)
        return "Please enter a command."
    
    def get_snapshot(self):
        """A dedicated function called by the Snapshot button."""
        return self.jarvis.run_daily_snapshot()

# --- NEW: Global Hotkey Logic ---
# The key combination to toggle the window
HOTKEY = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.KeyCode.from_char('j')} # For macOS
# For Windows, you would use:
# HOTKEY = {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char('j')}

# The set of keys currently being pressed
current_keys = set()

def toggle_window():
    """Show or hide the Jarvis window."""
    if window.hidden:
        window.show()
    else:
        window.hide()

def on_press(key):
    """Callback function for when a key is pressed."""
    if key in HOTKEY:
        current_keys.add(key)
        if all(k in current_keys for k in HOTKEY):
            # If all hotkeys are pressed, toggle the window
            toggle_window()

def on_release(key):
    """Callback function for when a key is released."""
    try:
        current_keys.remove(key)
    except KeyError:
        pass

# --- Main Execution Block ---
if __name__ == '__main__':
    api = Api()
    
    # Create the window, but start it hidden
    window = webview.create_window(
        'Jarvis',
        'gui/index.html',
        js_api=api,
        width=550,
        height=400,
        resizable=True,
        hidden=True, # Start the window hidden
        on_top=True
    )
    api.window = window
    
    # Start the keyboard listener in a separate thread
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    print("🚀 Jarvis is running in the background. Press Command+Shift+J to show/hide.")
    
    # Start the GUI event loop
    webview.start(debug=False)

    # Ensure the listener stops when the app closes
    listener.stop()