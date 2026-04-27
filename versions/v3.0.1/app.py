"""
ACEest Fitness & Gym - v3.0.1
Added role-based login (Admin/Trainer) and membership expiry tracking.
"""
import hashlib
import os
import sqlite3
from datetime import date, timedelta
from functools import wraps
from flask import Flask, g, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

PROGRAMS = {
    "Weight Loss": {"calories": 1800},
    "Muscle Gain": {"calories": 2800},
    "General Fitness": {"calories": 2000},
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
        "<h2>ACEest v3.0.1 Login</h2>"
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
        "<h2>Dashboard ({{ role }})</h2>"
        "{% if expiring %}<p style='color:orange'>⚠ {{ expiring|length }} memberships expiring soon</p>{% endif %}"
        "<ul>{% for c in clients %}<li>{{ c.name }} — {{ c.program }} | expires: {{ c.membership_expiry or 'N/A' }}</li>{% endfor %}</ul>"
        "<a href='/clients/add'>Add Client</a> | <a href='/logout'>Logout</a>",
        role=session.get("role"), clients=clients, expiring=expiring
    )


@app.route("/clients/add", methods=["GET", "POST"])
@login_required
def add_client():
    if request.method == "POST":
        name = request.form["name"]
        program = request.form.get("program", "General Fitness")
        calories = PROGRAMS.get(program, PROGRAMS["General Fitness"])["calories"]
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO clients (name,program,calories,membership_expiry) VALUES (?,?,?,?)",
            (name, program, calories, request.form.get("membership_expiry"))
        )
        db.commit()
        return redirect(url_for("dashboard"))
    return render_template_string(
        "<form method='post'>Name:<input name='name'> Program:<input name='program'> Expiry:<input name='membership_expiry' type='date'> <button>Add</button></form>"
    )


@app.route("/health")
def health():
    return {"status": "ok", "version": "3.0.1"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
