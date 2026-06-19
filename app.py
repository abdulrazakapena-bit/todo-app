from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

database_url = os.environ.get('DATABASE_URL', 'sqlite:///todos.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_TIMEOUT'] = 15

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    todos = db.relationship('Todo', backref='user', lazy=True)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def home():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", todos=todos)

@app.route("/add", methods=["POST"])
@login_required
def add():
    task = request.form.get("task")
    due_date_str = request.form.get("due_date")
    due_date = None
    if due_date_str:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
    if task:
        todo = Todo(text=task, done=False, due_date=due_date, user_id=current_user.id)
        db.session.add(todo)
        db.session.commit()
    return redirect(url_for("home"))

@app.route("/complete/<int:id>")
@login_required
def complete(id):
    todo = Todo.query.get_or_404(id)
    todo.done = True
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        if len(username) < 3:
            flash("Username must be at least 3 characters long.")
            return redirect(url_for("register"))

        if not username.isalnum():
            flash("Username can only contain letters and numbers, no spaces or symbols.")
            return redirect(url_for("register"))

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address e.g. yourname@gmail.com")
            return redirect(url_for("register"))

        if " " in email:
            flash("Email address cannot contain spaces.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect(url_for("register"))

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

        if not all([has_upper, has_lower, has_digit, has_special]):
            flash("Password must contain: uppercase, lowercase, number and special character e.g. Hello1@b")
            return redirect(url_for("register"))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("This email is already registered. Please login instead.")
            return redirect(url_for("register"))

        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash("This username is already taken. Please choose another one.")
            return redirect(url_for("register"))

        code = str(random.randint(100000, 999999))

        session['pending_user'] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'code': code,
            'expires': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }

        try:
            msg = Message(
                subject="Your verification code",
                sender=os.environ.get('MAIL_USERNAME'),
                recipients=[email]
            )
            msg.body = f"Hi {username},\n\nYour verification code is: {code}\n\nThis code expires in 10 minutes.\n\nIf you did not request this, ignore this email."
            mail.send(msg)
            flash("A 6-digit verification code has been sent to your email!")
        except Exception as e:
            flash(f"Could not send email. Error: {str(e)}")
            return redirect(url_for("register"))

        return redirect(url_for("verify"))

    return render_template("register.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        entered_code = request.form.get("code")
        pending = session.get('pending_user')

        if not pending:
            flash("Session expired. Please register again.")
            return redirect(url_for("register"))

        expires = datetime.fromisoformat(pending['expires'])
        if datetime.utcnow() > expires:
            session.pop('pending_user', None)
            flash("Code expired. Please register again.")
            return redirect(url_for("register"))

        if entered_code == pending['code']:
            user = User(
                username=pending['username'],
                email=pending['email'],
                password=pending['password']
            )
            db.session.add(user)
            db.session.commit()
            session.pop('pending_user', None)
            login_user(user)
            flash("Account created successfully!")
            return redirect(url_for("home"))
        else:
            flash("Invalid code. Please try again.")

    return render_template("verify.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))
        flash("Invalid email or password!")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")