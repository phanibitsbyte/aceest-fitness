"""
ACEest Fitness & Gym - v3.2.4
Full-featured Flask web application:
  - Role-based login (Admin / Trainer)
  - Client CRUD with program assignment and calorie targets
  - Weekly adherence progress tracking
  - Workout session logging
  - PDF client report generation
  - AI-style fitness program generator
  - Membership expiry management
  - Chart data JSON API
"""
import hashlib
import json
import os
import random
import sqlite3
import tempfile
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, g, redirect, render_template,
                   request, send_file, session, url_for)
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

PROGRAMS = {
    "Weight Loss": {
        "calories": 1800,
        "diet": "High protein, low carb. 4 meals/day. Caloric deficit of 500 kcal.",
        "exercises": ["Cardio 30 min", "HIIT 20 min", "Strength training 3x/week"],
    },
    "Muscle Gain": {
        "calories": 2800,
        "diet": "High protein (2g/kg), moderate carb. 5 meals/day. Caloric surplus.",
        "exercises": ["Heavy compound lifts 4x/week", "Accessory work", "Rest 1 min between sets"],
    },
    "Endurance": {
        "calories": 2200,
        "diet": "Complex carbs focus. Pre/post workout nutrition. Electrolyte balance.",
        "exercises": ["Running 5x/week", "Cycling 2x/week", "Swimming 1x/week"],
    },
    "General Fitness": {
        "calories": 2000,
        "diet": "Balanced macros (40/30/30 C/P/F). 3 meals + 2 snacks. Hydration focus.",
        "exercises": ["Full-body workout 3x/week", "Cardio 2x/week", "Yoga 1x/week"],
    },
    "Body Recomp": {
        "calories": 2100,
        "diet": "High protein, cycling carbs. 4-5 meals/day. Track macros precisely.",
        "exercises": ["Resistance training 4x/week", "LISS cardio 3x/week", "Progressive overload"],
    },
}

AI_EXERCISE_POOL = [
    "Push-ups 3x15", "Pull-ups 3x10", "Squats 4x12", "Deadlifts 3x8",
    "Bench Press 3x10", "Plank 3x60s", "Lunges 3x12 each", "Burpees 3x10",
    "Dumbbell rows 3x12", "Shoulder press 3x10", "Leg press 4x12", "Cable rows 3x12",
    "Tricep dips 3x15", "Bicep curls 3x12", "Leg curls 3x12", "Calf raises 4x15",
]


# ─── Database helpers ─────────────────────────────────────────────────────────

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
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'Trainer'
        );
        CREATE TABLE IF NOT EXISTS clients (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT UNIQUE NOT NULL,
            age              INTEGER,
            height           REAL,
            weight           REAL,
            program          TEXT,
            calories         INTEGER,
            target_weight    REAL,
            target_adherence REAL DEFAULT 80.0,
            membership_expiry TEXT
        );
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week        INTEGER,
            adherence   REAL
        );
        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT NOT NULL,
            date         TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes        TEXT
        );
        CREATE TABLE IF NOT EXISTS exercises (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name       TEXT,
            sets       INTEGER,
            reps       INTEGER,
            weight     REAL
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date        TEXT,
            weight      REAL,
            waist       REAL,
            bodyfat     REAL
        );
    """)
    pw = hashlib.sha256("admin".encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?,?,?)",
               ("admin", pw, "Admin"))
    db.commit()
    db.close()


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    clients = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    today = date.today().isoformat()
    expiring = [
        c for c in clients
        if c["membership_expiry"] and c["membership_expiry"] <= (
            date.today() + timedelta(days=30)
        ).isoformat()
    ]
    return render_template(
        "dashboard.html",
        clients=clients,
        expiring=expiring,
        programs=list(PROGRAMS.keys()),
        today=today,
    )


@app.route("/clients", methods=["GET", "POST"])
@login_required
def clients():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"]
        age = request.form.get("age") or 0
        height = request.form.get("height") or 0
        weight = request.form.get("weight") or 0
        program = request.form.get("program", "General Fitness")
        target_weight = request.form.get("target_weight") or 0
        membership_expiry = request.form.get("membership_expiry") or None
        calories = PROGRAMS.get(program, PROGRAMS["General Fitness"])["calories"]
        db.execute(
            """INSERT OR IGNORE INTO clients
               (name,age,height,weight,program,calories,target_weight,membership_expiry)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, age, height, weight, program, calories, target_weight, membership_expiry),
        )
        db.commit()
        return redirect(url_for("client_detail", name=name))
    rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return render_template("clients.html", clients=rows, programs=list(PROGRAMS.keys()))


@app.route("/clients/<name>", methods=["GET", "POST"])
@login_required
def client_detail(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return render_template("404.html"), 404
    if request.method == "POST":
        program = request.form.get("program", client["program"])
        target_weight = request.form.get("target_weight") or client["target_weight"]
        target_adherence = request.form.get("target_adherence") or client["target_adherence"]
        membership_expiry = request.form.get("membership_expiry") or client["membership_expiry"]
        calories = PROGRAMS.get(program, PROGRAMS["General Fitness"])["calories"]
        db.execute(
            """UPDATE clients SET program=?,calories=?,target_weight=?,
               target_adherence=?,membership_expiry=? WHERE name=?""",
            (program, calories, target_weight, target_adherence, membership_expiry, name),
        )
        db.commit()
        client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    progress = db.execute(
        "SELECT * FROM progress WHERE client_name=? ORDER BY week", (name,)
    ).fetchall()
    recent_workouts = db.execute(
        "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC LIMIT 5", (name,)
    ).fetchall()
    program_info = PROGRAMS.get(client["program"] or "General Fitness", PROGRAMS["General Fitness"])
    return render_template(
        "client_detail.html",
        client=client,
        programs=list(PROGRAMS.keys()),
        progress=progress,
        recent_workouts=recent_workouts,
        program_info=program_info,
    )


@app.route("/clients/<name>/progress", methods=["POST"])
@login_required
def save_progress(name):
    db = get_db()
    client = db.execute("SELECT id FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return render_template("404.html"), 404
    week = request.form.get("week", 1)
    adherence = request.form.get("adherence", 0)
    db.execute(
        "INSERT INTO progress (client_name,week,adherence) VALUES (?,?,?)",
        (name, week, adherence),
    )
    db.commit()
    return redirect(url_for("client_detail", name=name))


@app.route("/clients/<name>/workouts", methods=["GET", "POST"])
@login_required
def workouts(name):
    db = get_db()
    client = db.execute("SELECT id FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return render_template("404.html"), 404
    if request.method == "POST":
        workout_date = request.form.get("date", date.today().isoformat())
        wtype = request.form.get("workout_type", "Strength")
        duration = request.form.get("duration_min", 0)
        notes = request.form.get("notes", "")
        db.execute(
            "INSERT INTO workouts (client_name,date,workout_type,duration_min,notes) VALUES (?,?,?,?,?)",
            (name, workout_date, wtype, duration, notes),
        )
        db.commit()
        return redirect(url_for("workouts", name=name))
    rows = db.execute(
        "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC", (name,)
    ).fetchall()
    return render_template("workouts.html", client_name=name, workouts=rows)


@app.route("/clients/<name>/report")
@login_required
def generate_report(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return render_template("404.html"), 404
    progress = db.execute(
        "SELECT * FROM progress WHERE client_name=? ORDER BY week", (name,)
    ).fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "ACEest Fitness & Gym", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"Client Report: {client['name']}", ln=True, align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.ln(4)

    fields = [
        ("Age", client["age"]),
        ("Height (cm)", client["height"]),
        ("Weight (kg)", client["weight"]),
        ("Program", client["program"]),
        ("Daily Calories", client["calories"]),
        ("Target Weight", client["target_weight"]),
        ("Membership Expiry", client["membership_expiry"] or "N/A"),
    ]
    for label, value in fields:
        pdf.cell(60, 8, f"{label}:", border=0)
        pdf.cell(0, 8, str(value) if value is not None else "-", ln=True)

    if progress:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Weekly Adherence History", ln=True)
        pdf.set_font("Helvetica", size=10)
        for row in progress:
            pdf.cell(0, 7, f"  Week {row['week']}: {row['adherence']}%", ln=True)

    pdf_dir = tempfile.gettempdir()
    pdf_path = os.path.join(pdf_dir, f"{name.replace(' ', '_')}_report.pdf")
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{name}_report.pdf", mimetype="application/pdf")


@app.route("/clients/<name>/generate-program")
@login_required
def generate_program(name):
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        return render_template("404.html"), 404
    exercises = random.sample(AI_EXERCISE_POOL, 6)
    program_info = PROGRAMS.get(client["program"] or "General Fitness", PROGRAMS["General Fitness"])
    return render_template(
        "client_detail.html",
        client=client,
        programs=list(PROGRAMS.keys()),
        progress=[],
        recent_workouts=[],
        program_info=program_info,
        generated_program=exercises,
    )


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


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=5000)
