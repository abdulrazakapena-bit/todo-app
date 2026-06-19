from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

database_url = os.environ.get('DATABASE_URL', 'sqlite:///todos.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.DateTime, nullable=True)

@app.route("/")
def home():
    todos = Todo.query.all()
    return render_template("index.html", todos=todos)

@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task")
    due_date_str = request.form.get("due_date")
    due_date = None
    if due_date_str:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
    if task:
        todo = Todo(text=task, done=False, due_date=due_date)
        db.session.add(todo)
        db.session.commit()
    return redirect(url_for("home"))

@app.route("/complete/<int:id>")
def complete(id):
    todo = Todo.query.get_or_404(id)
    todo.done = True
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")