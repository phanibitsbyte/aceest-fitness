"""
ACEest Fitness & Gym - v2.2.4
Added workout session logging, exercise tracking per session.
"""
import os
import sqlite3
from datetime import date
from flask import Flask, g, redirect, render_template_string, request, url_for

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
            name TEXT UNIQUE, age INTEGER,
            height REAL, weight REAL,
            program TEXT, calories INTEGER,
            target_weight REAL, target_adherence INTEGER DEFAULT 80
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT, week TEXT, adherence INTEGER
        );
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT, date TEXT,
            workout_type TEXT, duration_min INTEGER, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER, name TEXT,
            sets INTEGER, reps INTEGER, weight REAL
        );
    """)
    db.commit()
    db.close()


@app.route("/")
def index():
    db = get_db()
    clients = db.execute("SELECT name, program FROM clients ORDER BY name").fetchall()
    return render_template_string(
        "<h2>ACEest v2.2.4</h2><ul>{% for c in clients %}<li><a href='/clients/{{ c.name }}'>{{ c.name }}</a></li>{% endfor %}</ul><a href='/clients/add'>Add Client</a>",
        clients=clients
    )


@app.route("/clients/add", methods=["GET", "POST"])
def add_client():
    if request.method == "POST":
        name = request.form["name"]
        weight = float(request.form.get("weight", 0) or 0)
        program = request.form.get("program", "Fat Loss (FL)")
        calories = int(weight * PROGRAMS.get(program, {"factor": 25})["factor"])
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO clients (name,weight,program,calories) VALUES (?,?,?,?)",
            (name, weight, program, calories)
        )
        db.commit()
        return redirect(url_for("client_detail", name=name))
    return "<form method='post'>Name:<input name='name'> Weight:<input name='weight' type='number'> Program:<input name='program'> <button>Add</button></form>"


@app.route("/clients/<name>")
def client_detail(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    workouts = db.execute(
        "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC LIMIT 10", (name,)
    ).fetchall()
    return render_template_string(
        "<h2>{{ client.name }} — {{ client.program }}</h2>"
        "<h3>Recent Workouts</h3><ul>{% for w in workouts %}<li>{{ w.date }} {{ w.workout_type }} {{ w.duration_min }}min</li>{% endfor %}</ul>"
        "<a href='/clients/{{ client.name }}/workouts/add'>Log Workout</a>",
        client=client, workouts=workouts
    )


@app.route("/clients/<name>/workouts/add", methods=["GET", "POST"])
def add_workout(name):
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO workouts (client_name,date,workout_type,duration_min,notes) VALUES (?,?,?,?,?)",
            (name, request.form.get("date", date.today().isoformat()),
             request.form.get("type", "Strength"),
             int(request.form.get("duration", 60) or 60),
             request.form.get("notes", ""))
        )
        db.commit()
        return redirect(url_for("client_detail", name=name))
    return f"<form method='post'>Date:<input name='date' value='{date.today().isoformat()}'> Type:<input name='type'> Duration:<input name='duration' type='number' value='60'> Notes:<input name='notes'> <button>Save</button></form>"


@app.route("/health")
def health():
    return {"status": "ok", "version": "2.2.4"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
