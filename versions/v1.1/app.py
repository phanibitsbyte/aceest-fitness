"""
ACEest Fitness & Gym - v1.1
Enhanced program display with calorie estimation and client profile form.
"""
from flask import Flask, render_template_string, request

app = Flask(__name__)

PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": "Mon: Back Squat 5x5 + Core\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: Deadlift + Box Jumps\nFri: Zone 2 Cardio 30min",
        "diet": "Breakfast: Egg Whites + Oats\nLunch: Grilled Chicken + Brown Rice\nDinner: Fish Curry + Millet Roti\nTarget: ~2000 kcal",
        "calorie_factor": 22,
    },
    "Muscle Gain (MG)": {
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "Breakfast: Eggs + Peanut Butter Oats\nLunch: Chicken Biryani\nDinner: Mutton Curry + Rice\nTarget: ~3200 kcal",
        "calorie_factor": 35,
    },
    "Beginner (BG)": {
        "workout": "Full Body Circuit:\n- Air Squats\n- Ring Rows\n- Push-ups\nFocus: Technique & Consistency",
        "diet": "Balanced Tamil Meals\nIdli / Dosa / Rice + Dal\nProtein Target: 120g/day",
        "calorie_factor": 26,
    },
}

TEMPLATE = """
<!DOCTYPE html><html><head><title>ACEest Fitness v1.1</title></head>
<body style="background:#1a1a1a;color:white;font-family:Arial;padding:20px;">
<h1 style="color:#d4af37;">ACEest Functional Fitness System v1.1</h1>
<form method="post">
  Name: <input name="name" value="{{ name }}" style="background:#333;color:white;margin:5px;">
  Weight (kg): <input name="weight" type="number" step="0.1" value="{{ weight }}" style="background:#333;color:white;margin:5px;">
  Program:
  <select name="program" style="background:#333;color:white;margin:5px;">
    {% for p in programs %}<option {% if p == selected %}selected{% endif %}>{{ p }}</option>{% endfor %}
  </select>
  <button type="submit" style="background:#d4af37;padding:5px 15px;">View Plan</button>
</form>
{% if selected and data %}
<div style="border:1px solid #d4af37;padding:15px;margin:15px 0;">
  <h2>{{ selected }}</h2>
  {% if weight > 0 %}<p style="color:#d4af37;">Estimated Calories: {{ (weight * data.calorie_factor)|int }} kcal/day</p>{% endif %}
  <h3>Workout Plan</h3><pre>{{ data.workout }}</pre>
  <h3>Diet Plan</h3><pre>{{ data.diet }}</pre>
</div>
{% endif %}
</body></html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    name = ""
    weight = 0.0
    selected = None
    data = None
    if request.method == "POST":
        name = request.form.get("name", "")
        weight = float(request.form.get("weight", 0) or 0)
        selected = request.form.get("program")
        data = PROGRAMS.get(selected)
    return render_template_string(
        TEMPLATE, programs=list(PROGRAMS.keys()),
        name=name, weight=weight, selected=selected, data=data
    )


@app.route("/health")
def health():
    return {"status": "ok", "version": "1.1"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
