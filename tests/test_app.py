"""
Pytest test suite for ACEest Fitness & Gym Flask application.
Covers: app creation, authentication, client CRUD, client update,
progress persistence, workouts persistence, logout, index redirect,
AI program generation, PDF report, and JSON chart API.
"""

import os
import pytest

# Use a dedicated test DB — must be set BEFORE importing app
os.environ["DB_NAME"] = "test_aceest.db"

from app import app as flask_app, init_db, PROGRAMS  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
    })
    with flask_app.app_context():
        init_db()
    yield flask_app
    if os.path.exists("test_aceest.db"):
        os.remove("test_aceest.db")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client pre-logged in as admin."""
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client


@pytest.fixture
def sample_client_name():
    return "TestUser"


@pytest.fixture
def create_client(auth_client, sample_client_name):
    """Create a sample gym client with a valid program name."""
    auth_client.post("/clients", data={
        "name": sample_client_name,
        "age": "28",
        "height": "175",
        "weight": "80",
        "program": "Weight Loss",
        "target_weight": "70",
        "target_adherence": "85",
        "membership_expiry": "2026-12-31",
    })
    return sample_client_name


# ---------------------------------------------------------------------------
# Test 1: App Creation & Config
# ---------------------------------------------------------------------------

def test_app_creation(app):
    """App should be created with TESTING flag enabled."""
    assert app.testing is True
    assert app.secret_key == "test-secret"


# ---------------------------------------------------------------------------
# Test 2: Index redirects to login when unauthenticated
# ---------------------------------------------------------------------------

def test_index_redirects_to_login(client):
    """GET / without a session should redirect to /login."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Test 3: Index redirects to dashboard when authenticated
# ---------------------------------------------------------------------------

def test_index_redirects_to_dashboard_when_logged_in(auth_client):
    """GET / with active session should redirect to /dashboard."""
    response = auth_client.get("/")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Test 4: Login page loads
# ---------------------------------------------------------------------------

def test_login_page_loads(client):
    """GET /login should return 200 with ACEest branding."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"ACEest" in response.data


# ---------------------------------------------------------------------------
# Test 5: Successful login
# ---------------------------------------------------------------------------

def test_login_success(client):
    """Valid credentials should redirect to /dashboard."""
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Test 6: Failed login shows error
# ---------------------------------------------------------------------------

def test_login_failure(client):
    """Invalid credentials should return 200 with an error message."""
    response = client.post("/login", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 200
    assert b"Invalid" in response.data


# ---------------------------------------------------------------------------
# Test 7: Logout clears session and redirects
# ---------------------------------------------------------------------------

def test_logout(app):
    """Logout should clear session and redirect to /login."""
    with app.test_client() as c:
        c.post("/login", data={"username": "admin", "password": "admin"})
        # Confirm logged in
        assert c.get("/dashboard").status_code == 200
        # Logout
        response = c.get("/logout")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
        # Subsequent protected request should redirect to login
        assert c.get("/dashboard").status_code == 302


# ---------------------------------------------------------------------------
# Test 8: Dashboard requires auth
# ---------------------------------------------------------------------------

def test_dashboard_requires_auth(client):
    """GET /dashboard without session should redirect to /login."""
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Test 9: Dashboard accessible after login
# ---------------------------------------------------------------------------

def test_dashboard_accessible_after_login(auth_client):
    """GET /dashboard after login should return 200 with Dashboard heading."""
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


# ---------------------------------------------------------------------------
# Test 10: Client list page loads
# ---------------------------------------------------------------------------

def test_clients_page_loads(auth_client):
    """GET /clients should return 200 with the add-client form."""
    response = auth_client.get("/clients")
    assert response.status_code == 200
    assert b"Client" in response.data


# ---------------------------------------------------------------------------
# Test 11: Add client — redirect and data persisted
# ---------------------------------------------------------------------------

def test_add_client_redirect(auth_client):
    """POST /clients should create client and redirect to detail page."""
    response = auth_client.post("/clients", data={
        "name": "Priya Sharma",
        "age": "30",
        "height": "162",
        "weight": "65",
        "program": "Muscle Gain",
        "target_weight": "68",
        "membership_expiry": "2026-06-30",
    })
    assert response.status_code == 302
    assert "Priya" in response.headers["Location"]


def test_add_client_data_persisted(auth_client):
    """After POST /clients, client detail page should show the saved data."""
    auth_client.post("/clients", data={
        "name": "Ravi Kumar",
        "age": "35",
        "height": "178",
        "weight": "90",
        "program": "Body Recomp",
        "target_weight": "82",
        "membership_expiry": "2027-01-01",
    })
    response = auth_client.get("/clients/Ravi%20Kumar")
    assert response.status_code == 200
    assert b"Ravi Kumar" in response.data
    assert b"Body Recomp" in response.data


def test_add_client_calories_from_programs(auth_client):
    """Calories assigned to new client must match the PROGRAMS dict value."""
    program = "Endurance"
    expected_calories = PROGRAMS[program]["calories"]
    auth_client.post("/clients", data={
        "name": "Endurance Tester",
        "age": "25",
        "weight": "70",
        "program": program,
    })
    response = auth_client.get("/clients/Endurance%20Tester")
    assert response.status_code == 200
    assert str(expected_calories).encode() in response.data


# ---------------------------------------------------------------------------
# Test 14: Client detail page loads
# ---------------------------------------------------------------------------

def test_client_detail_page_loads(auth_client, create_client):
    """GET /clients/<name> should return 200 with client name."""
    response = auth_client.get(f"/clients/{create_client}")
    assert response.status_code == 200
    assert create_client.encode() in response.data


# ---------------------------------------------------------------------------
# Test 15: Client detail shows program exercises
# ---------------------------------------------------------------------------

def test_client_detail_shows_program_info(auth_client, create_client):
    """Client detail page must render the program's exercises."""
    response = auth_client.get(f"/clients/{create_client}")
    # "Weight Loss" program has "Cardio 30 min" exercise
    assert b"Cardio" in response.data


# ---------------------------------------------------------------------------
# Test 16: Client not found returns 404
# ---------------------------------------------------------------------------

def test_client_not_found(auth_client):
    """GET /clients/<nonexistent> should return 404."""
    response = auth_client.get("/clients/NonExistentClient99")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 17: Update client
# ---------------------------------------------------------------------------

def test_update_client(auth_client, create_client):
    """POST /clients/<name> should update client fields in the database."""
    response = auth_client.post(f"/clients/{create_client}", data={
        "program": "Muscle Gain",
        "target_weight": "75",
        "target_adherence": "90",
        "membership_expiry": "2027-06-30",
    })
    assert response.status_code == 200
    # Verify updated values appear on the page
    assert b"Muscle Gain" in response.data
    assert b"75" in response.data


# ---------------------------------------------------------------------------
# Test 18: Save weekly progress — persisted and visible
# ---------------------------------------------------------------------------

def test_save_progress_redirect(auth_client, create_client):
    """POST /clients/<name>/progress should redirect back to client detail."""
    response = auth_client.post(
        f"/clients/{create_client}/progress",
        data={"week": "1", "adherence": "80"},
    )
    assert response.status_code == 302
    assert create_client in response.headers["Location"]


def test_save_progress_data_persisted(auth_client, create_client):
    """Progress entry should appear on the client detail page after saving."""
    auth_client.post(
        f"/clients/{create_client}/progress",
        data={"week": "2", "adherence": "75"},
    )
    response = auth_client.get(f"/clients/{create_client}")
    assert response.status_code == 200
    assert b"75" in response.data


# ---------------------------------------------------------------------------
# Test 20: Progress for non-existent client returns 404
# ---------------------------------------------------------------------------

def test_save_progress_client_not_found(auth_client):
    """POST progress for unknown client should return 404."""
    response = auth_client.post(
        "/clients/GhostClient/progress",
        data={"week": "1", "adherence": "50"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 21: Log workout — persisted and visible
# ---------------------------------------------------------------------------

def test_log_workout_redirect(auth_client, create_client):
    """POST /clients/<name>/workouts should redirect after logging."""
    response = auth_client.post(
        f"/clients/{create_client}/workouts",
        data={
            "date": "2026-03-07",
            "workout_type": "Strength",
            "duration_min": "60",
            "notes": "Back Squat 5x5",
        },
    )
    assert response.status_code == 302


def test_log_workout_data_persisted(auth_client, create_client):
    """Logged workout should appear in the workouts list."""
    auth_client.post(
        f"/clients/{create_client}/workouts",
        data={
            "date": "2026-03-08",
            "workout_type": "Cardio",
            "duration_min": "45",
            "notes": "5km run",
        },
    )
    response = auth_client.get(f"/clients/{create_client}/workouts")
    assert response.status_code == 200
    assert b"Cardio" in response.data
    assert b"5km run" in response.data


# ---------------------------------------------------------------------------
# Test 23: Workout page for non-existent client returns 404
# ---------------------------------------------------------------------------

def test_workouts_client_not_found(auth_client):
    """GET /clients/<nonexistent>/workouts should return 404."""
    response = auth_client.get("/clients/GhostClient/workouts")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 24: Workout list page loads
# ---------------------------------------------------------------------------

def test_workouts_page_loads(auth_client, create_client):
    """GET /clients/<name>/workouts should return 200."""
    response = auth_client.get(f"/clients/{create_client}/workouts")
    assert response.status_code == 200
    assert b"Workout" in response.data


# ---------------------------------------------------------------------------
# Test 25: AI program generation
# ---------------------------------------------------------------------------

def test_generate_program_returns_200(auth_client, create_client):
    """GET /clients/<name>/generate-program should return 200."""
    response = auth_client.get(f"/clients/{create_client}/generate-program")
    assert response.status_code == 200


def test_generate_program_shows_exercises(auth_client, create_client):
    """Generated program page must contain exercise names from AI pool."""
    from app import AI_EXERCISE_POOL
    response = auth_client.get(f"/clients/{create_client}/generate-program")
    assert response.status_code == 200
    # At least one exercise from the pool must appear
    found = any(ex.split()[0].encode() in response.data for ex in AI_EXERCISE_POOL)
    assert found, "No AI exercises found in generated program response"


def test_generate_program_client_not_found(auth_client):
    """GET generate-program for non-existent client should return 404."""
    response = auth_client.get("/clients/GhostClient/generate-program")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 28: Chart API — structure and populated data
# ---------------------------------------------------------------------------

def test_chart_data_structure(auth_client, create_client):
    """GET chart API should return JSON with 'labels' and 'values' keys."""
    response = auth_client.get(f"/api/clients/{create_client}/chart")
    assert response.status_code == 200
    data = response.get_json()
    assert "labels" in data
    assert "values" in data
    assert isinstance(data["labels"], list)
    assert isinstance(data["values"], list)


def test_chart_data_populated_after_progress(auth_client, create_client):
    """Chart API values must reflect adherence entries saved for the client."""
    auth_client.post(
        f"/clients/{create_client}/progress",
        data={"week": "3", "adherence": "92"},
    )
    response = auth_client.get(f"/api/clients/{create_client}/chart")
    data = response.get_json()
    assert len(data["values"]) >= 1
    assert 92.0 in [float(v) for v in data["values"]]
    # Labels must follow "Week N" format
    assert any("Week" in lbl for lbl in data["labels"])


# ---------------------------------------------------------------------------
# Test 30: PDF report generated
# ---------------------------------------------------------------------------

def test_generate_pdf_report(auth_client, create_client):
    """GET /clients/<name>/report should return a valid PDF file."""
    response = auth_client.get(f"/clients/{create_client}/report")
    assert response.status_code == 200
    assert response.content_type == "application/pdf"
    # PDF binary starts with %PDF
    assert response.data[:4] == b"%PDF"


def test_generate_pdf_report_client_not_found(auth_client):
    """GET report for non-existent client should return 404."""
    response = auth_client.get("/clients/GhostClient/report")
    assert response.status_code == 404
