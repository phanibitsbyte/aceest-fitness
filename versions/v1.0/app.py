"""
ACEest Fitness & Gym - v1.0
Basic Flask web application: static program display (Fat Loss, Muscle Gain, Beginner).
"""
from flask import Flask, render_template_string

app = Flask(__name__)

PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": "Mon: 5x5 Back Squat + AMRAP\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: 10RFT Deadlifts/Box Jumps\nFri: 30min Active Recovery",
        "diet": "B: 3 Egg Whites + Oats\nL: Grilled Chicken + Brown Rice\nD: Fish Curry + Millet Roti\nTarget: 2,000 kcal",
    },
    "Muscle Gain (MG)": {
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "B: 4 Eggs + PB Oats\nL: Chicken Biryani (250g Chicken)\nD: Mutton Curry + Jeera Rice\nTarget: 3,200 kcal",
    },
    "Beginner (BG)": {
        "workout": "Circuit Training: Air Squats, Ring Rows, Push-ups.\nFocus: Technique Mastery & Form",
        "diet": "Balanced Meals: Idli-Sambar, Rice-Dal, Chapati.\nProtein: 120g/day",
    },
}

TEMPLATE = """
<!DOCTYPE html><html><head><title>ACEest Fitness v1.0</title></head>
<body style="background:#1a1a1a;color:white;font-family:Arial;padding:20px;">
<h1 style="color:#d4af37;">ACEest Functional Fitness v1.0</h1>
{% for name, data in programs.items() %}
<div style="border:1px solid #d4af37;padding:15px;margin:10px 0;">
  <h2>{{ name }}</h2>
  <h3>Workout Plan</h3><pre>{{ data.workout }}</pre>
  <h3>Diet Plan</h3><pre>{{ data.diet }}</pre>
</div>
{% endfor %}
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(TEMPLATE, programs=PROGRAMS)


@app.route("/health")
def health():
    return {"status": "ok", "version": "1.0"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
