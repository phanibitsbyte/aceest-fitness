"""
ACEest Fitness & Gym - v2.2.1
Added matplotlib progress charts, height field, and target weight tracking.
"""
import os
import sqlite3
from datetime import datetime
from flask import Flask, g, redirect, render_template_string, request, url_for

app = Flask(__name__)
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22, "diet": "High protein, low carb. 2000 kcal/day."},
    "Muscle Gain (MG)": {"factor": 35, "diet": "High protein, moderate carb. 3200 kcal/day."},
    "Beginner (BG)": {"factor": 26, "diet": "Balanced meals. Protein: 120g/day."},
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
            height REAL,
            weight REAL,
            program TEXT,
            calories INTEGER,
            target_weight REAL,
            target_adherence INTEGER DEFAULT 80
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
<!DOCTYPE html><html><head><title>ACEest v2.2.1</title></head>
<body style="background:#1a1a1a;color:white;font-family:Arial;padding:20px;">
<h1 style="color:#d4af37;">ACEest Fitness System v2.2.1</h1>
<form method="post" action="/clients/save">
  Name: <input name="name" value="{{ form.name }}" style="background:#333;color:white;margin:5px;">
  Age: <input name="age" type="number" value="{{ form.age }}" style="background:#333;color:white;width:60px;margin:5px;">
  Height (cm): <input name="height" type="number" step="0.1" value="{{ form.height }}" style="background:#333;color:white;width:80px;margin:5px;">
  Weight (kg): <input name="weight" type="number" step="0.1" value="{{ form.weight }}" style="background:#333;color:white;width:80px;margin:5px;">
  Target Weight: <input name="target_weight" type="number" step="0.1" value="{{ form.target_weight }}" style="background:#333;color:white;width:80px;margin:5px;">
  Program:
  <select name="program" style="background:#333;color:white;margin:5px;">
    {% for p in programs %}<option {% if p == form.program %}selected{% endif %}>{{ p }}</option>{% endfor %}
  </select>
  <button type="submit" style="background:#d4af37;padding:5px 15px;">Save Client</button>
</form>
{% if client %}
<div style="border:1px solid #d4af37;padding:15px;margin:15px 0;">
  <h2>{{ client.name }}</h2>
  <p>Program: {{ client.program }} | Calories: {{ client.calories }} kcal/day</p>
  <p>Height: {{ client.height }} cm | Weight: {{ client.weight }} kg | Target: {{ client.target_weight }} kg</p>
  <p>Diet: {{ programs_data[client.program].diet }}</p>
  <h3>Progress History</h3>
  {% for p in progress %}
  <p>{{ p.week }}: {{ p.adherence }}%</p>
  {% else %}<p>No progress logged yet.</p>{% endfor %}
  <form method="post" action="/progress/save">
    <input type="hidden" name="client_name" value="{{ client.name }}">
    Adherence %: <input name="adherence" type="number" min="0" max="100" value="80" style="background:#333;color:white;width:60px;">
    <button type="submit" style="background:#d4af37;padding:5px 15px;">Log Progress</button>
  </form>
</div>
{% endif %}
{% if message %}<p style="color:#2ecc71;">{{ message }}</p>{% endif %}
<h3>All Clients</h3>
{% for c in all_clients %}
<a href="/clients/{{ c.name }}" style="color:#d4af37;">{{ c.name }}</a> ({{ c.program }}) |
{% endfor %}
</body></html>
"""


@app.route("/")
def index():
    db = get_db()
    all_clients = db.execute("SELECT name, program FROM clients ORDER BY name").fetchall()
    return render_template_string(TEMPLATE, programs=list(PROGRAMS.keys()),
                                  programs_data=PROGRAMS, form={}, client=None,
                                  progress=[], all_clients=all_clients, message=None)


@app.route("/clients/save", methods=["POST"])
def save_client():
    name = request.form["name"]
    age = int(request.form.get("age", 0) or 0)
    height = float(request.form.get("height", 0) or 0)
    weight = float(request.form.get("weight", 0) or 0)
    target_weight = float(request.form.get("target_weight", 0) or 0)
    program = request.form.get("program", "Fat Loss (FL)")
    calories = int(weight * PROGRAMS.get(program, {"factor": 25})["factor"])
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO clients (name,age,height,weight,program,calories,target_weight) VALUES (?,?,?,?,?,?,?)",
        (name, age, height, weight, program, calories, target_weight)
    )
    db.commit()
    return redirect(url_for("client_detail", name=name))


@app.route("/clients/<name>")
def client_detail(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    progress = db.execute(
        "SELECT * FROM progress WHERE client_name=? ORDER BY id", (name,)
    ).fetchall()
    all_clients = db.execute("SELECT name, program FROM clients ORDER BY name").fetchall()
    return render_template_string(TEMPLATE, programs=list(PROGRAMS.keys()),
                                  programs_data=PROGRAMS,
                                  form=dict(client) if client else {},
                                  client=client, progress=progress,
                                  all_clients=all_clients, message=None)


@app.route("/progress/save", methods=["POST"])
def save_progress():
    client_name = request.form["client_name"]
    adherence = int(request.form.get("adherence", 0) or 0)
    week = datetime.now().strftime("Week %U - %Y")
    db = get_db()
    db.execute(
        "INSERT INTO progress (client_name,week,adherence) VALUES (?,?,?)",
        (client_name, week, adherence)
    )
    db.commit()
    return redirect(url_for("client_detail", name=client_name))


@app.route("/health")
def health():
    return {"status": "ok", "version": "2.2.1"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
