from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

todos = []

@app.route("/")
def home():
    return render_template("index.html", todos=todos)

@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task")
    if task:
        todos.append({"text": task, "done": False})
    return redirect(url_for("home"))

@app.route("/complete/<int:index>")
def complete(index):
    todos[index]["done"] = True
    return redirect(url_for("home"))

@app.route("/delete/<int:index>")
def delete(index):
    todos.pop(index)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")