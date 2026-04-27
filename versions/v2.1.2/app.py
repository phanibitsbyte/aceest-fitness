"""
ACEest Fitness & Gym - v2.1.2
Added SQLite persistence: client save/load and weekly progress tracking.
"""
import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, g

app = Flask(__name__)
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22},
    "Muscle Gain (MG)": {"factor": 35},
    "Beginner (BG)": {"factor": 26},
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DB_NAME)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            weight REAL,
            program TEXT,
            calories INTEGER
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        );
    """)
    db.commit()
    db.close()


TEMPLATE = """
<!DOCTYPE html><html><head><title>ACEest v2.1.2</title></head>
<body style="background:#1a1a1a;color:white;font-family:Arial;padding:20px;">
<h1 style="color:#d4af37;">ACEest Functional Fitness System v2.1.2</h1>
<h2>Client Management</h2>
<form method="post" action="/save">
  Name: <input name="name" value="{{ name }}" style="background:#333;color:white;margin:5px;">
  Age: <input name="age" type="number" value="{{ age }}" style="background:#333;color:white;margin:5px;width:60px;">
  Weight (kg): <input name="weight" type="number" step="0.1" value="{{ weight }}" style="background:#333;color:white;margin:5px;width:80px;">
  Program:
  <select name="program" style="background:#333;color:white;margin:5px;">
    {% for p in programs %}<option>{{ p }}</option>{% endfor %}
  </select>
  <button type="submit" style="background:#d4af37;padding:5px 15px;">Save Client</button>
</form>
<form method="post" action="/load">
  Load Client: <input name="name" style="background:#333;color:white;margin:5px;">
  <button type="submit" style="background:#d4af37;padding:5px 15px;">Load</button>
</form>
{% if client %}
<div style="border:1px solid #d4af37;padding:15px;margin:15px 0;">
  <h3>{{ client.name }} | {{ client.program }} | {{ client.calories }} kcal/day</h3>
</div>
{% endif %}
{% if message %}<p style="color:#2ecc71;">{{ message }}</p>{% endif %}
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(TEMPLATE, programs=list(PROGRAMS.keys()),
                                  name="", age=0, weight=0, client=None, message=None)


@app.route("/save", methods=["POST"])
def save_client():
    name = request.form["name"]
    age = int(request.form.get("age", 0) or 0)
    weight = float(request.form.get("weight", 0) or 0)
    program = request.form.get("program", "Fat Loss (FL)")
    calories = int(weight * PROGRAMS.get(program, {"factor": 25})["factor"])
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO clients (name,age,weight,program,calories) VALUES (?,?,?,?,?)",
        (name, age, weight, program, calories)
    )
    db.commit()
    return render_template_string(TEMPLATE, programs=list(PROGRAMS.keys()),
                                  name=name, age=age, weight=weight, client=None,
                                  message=f"Client {name} saved successfully!")


@app.route("/load", methods=["POST"])
def load_client():
    name = request.form["name"]
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    return render_template_string(TEMPLATE, programs=list(PROGRAMS.keys()),
                                  name=name, age=0, weight=0, client=client, message=None)


@app.route("/health")
def health():
    return {"status": "ok", "version": "2.1.2"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
