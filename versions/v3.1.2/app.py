"""
ACEest Fitness & Gym - v3.1.2
Added PDF report generation, AI-style program generator, and chart data API.
This is the pre-release version before v3.2.4 full feature set.
"""
import hashlib
import json
import os
import random
import sqlite3
import tempfile
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, g, redirect, render_template_string,
                   request, send_file, session, url_for)
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

PROGRAMS = {
    "Weight Loss": {"calories": 1800, "diet": "High protein, low carb. 4 meals/day."},
    "Muscle Gain": {"calories": 2800, "diet": "High protein (2g/kg), moderate carb. 5 meals/day."},
    "Endurance": {"calories": 2200, "diet": "Complex carbs focus. Pre/post workout nutrition."},
    "General Fitness": {"calories": 2000, "diet": "Balanced macros. 3 meals + 2 snacks."},
}

AI_EXERCISES = [
    "Push-ups 3x15", "Pull-ups 3x10", "Squats 4x12", "Deadlifts 3x8",
    "Bench Press 3x10", "Plank 3x60s", "Lunges 3x12", "Burpees 3x10",
]


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
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Trainer'
        );
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            age INTEGER, height REAL, weight REAL,
            program TEXT, calories INTEGER,
            target_weight REAL, target_adherence REAL DEFAULT 80.0,
            membership_expiry TEXT
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week INTEGER, adherence REAL
        );
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date TEXT, workout_type TEXT,
            duration_min INTEGER, notes TEXT
        );
    """)
    pw = hashlib.sha256("admin".encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES (?,?,?)",
               ("admin", pw, "Admin"))
    db.commit()
    db.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pw = hashlib.sha256(request.form["password"].encode()).hexdigest()
        user = get_db().execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form["username"], pw)
        ).fetchone()
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        error = "Invalid credentials"
    return render_template_string(
        "<h2>ACEest v3.1.2 Login</h2>"
        "{% if error %}<p style='color:red'>{{ error }}</p>{% endif %}"
        "<form method='post'>Username:<input name='username'> Password:<input name='password' type='password'> <button>Login</button></form>",
        error=error
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    clients = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    expiring = [c for c in clients if c["membership_expiry"] and
                c["membership_expiry"] <= (date.today() + timedelta(days=30)).isoformat()]
    return render_template_string(
        "<h2>ACEest v3.1.2 Dashboard ({{ role }})</h2>"
        "{% if expiring %}<p>⚠ {{ expiring|length }} expiring</p>{% endif %}"
        "<ul>{% for c in clients %}<li>{{ c.name }} | <a href='/clients/{{ c.name }}/report'>PDF</a> | <a href='/clients/{{ c.name }}/generate'>AI Plan</a></li>{% endfor %}</ul>"
        "<a href='/clients'>Manage Clients</a>",
        role=session.get("role"), clients=clients, expiring=expiring
    )


@app.route("/clients")
@login_required
def clients():
    db = get_db()
    rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return render_template_string(
        "<h2>Clients</h2><ul>{% for c in clients %}<li>{{ c.name }}</li>{% endfor %}</ul>",
        clients=rows
    )


@app.route("/clients/<name>/report")
@login_required
def generate_report(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return "Not found", 404
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, f"ACEest Report - {client['name']}", ln=True)
    pdf.set_font("Helvetica", size=11)
    for field in ["name", "program", "calories", "membership_expiry"]:
        pdf.cell(0, 8, f"{field}: {client[field]}", ln=True)
    pdf_path = os.path.join(tempfile.gettempdir(), f"{name}_report.pdf")
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{name}_report.pdf", mimetype="application/pdf")


@app.route("/clients/<name>/generate")
@login_required
def generate_program(name):
    exercises = random.sample(AI_EXERCISES, 5)
    return Response(json.dumps({"client": name, "program": exercises}),
                    mimetype="application/json")


@app.route("/api/clients/<name>/chart")
@login_required
def chart_data(name):
    db = get_db()
    rows = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY week", (name,)
    ).fetchall()
    data = {"labels": [f"Week {r['week']}" for r in rows],
            "values": [r["adherence"] for r in rows]}
    return Response(json.dumps(data), mimetype="application/json")


@app.route("/health")
def health():
    return {"status": "ok", "version": "3.1.2"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
