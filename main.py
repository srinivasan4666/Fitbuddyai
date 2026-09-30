import os
import html
import sqlite3
import requests

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# Load API settings
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

app = FastAPI(title="FitBuddy AI")

DB_NAME = "fitbuddy.db"


# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            goal TEXT,
            workout TEXT,
            feedback TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- GEMINI AI ----------------

def ask_gemini(prompt):
    if not API_KEY:
        return (
            "Gemini API key is missing. "
            "Please add your Google API key in the .env file."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=60
        )

        if response.status_code != 200:
            return (
                "Gemini API Error: "
                + response.text[:1000]
            )

        result = response.json()

        return (
            result["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."

    except Exception as e:
        return f"Error connecting to Gemini: {str(e)}"


# ---------------- HOME PAGE ----------------

@app.get("/", response_class=HTMLResponse)
def home():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FitBuddy AI</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>
            body {
                font-family: Arial, sans-serif;
                background: #eef4ff;
                margin: 0;
                padding: 20px;
            }

            .container {
                max-width: 650px;
                margin: auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 15px #cccccc;
            }

            h1 {
                text-align: center;
                color: #2356a8;
            }

            input, select, button {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                box-sizing: border-box;
                border-radius: 7px;
                border: 1px solid #ccc;
                font-size: 16px;
            }

            button {
                background: #2356a8;
                color: white;
                border: none;
                cursor: pointer;
            }

            button:hover {
                background: #173c7a;
            }

            .note {
                font-size: 13px;
                color: #555;
                line-height: 1.5;
            }
        </style>
    </head>

    <body>

    <div class="container">

        <h1>FitBuddy AI</h1>

        <p style="text-align:center">
            AI Fitness Plan Generator using Gemini
        </p>

        <form action="/generate" method="post">

            <label>Your Name</label>
            <input type="text" name="name"
                   placeholder="Enter your name"
                   required maxlength="60">

            <label>Age</label>
            <input type="number" name="age"
                   min="13" max="100"
                   placeholder="Enter your age"
                   required>

            <label>Fitness Goal</label>
            <select name="goal" required>
                <option value="">Select your goal</option>
                <option value="General fitness">
                    General Fitness
                </option>
                <option value="Weight management">
                    Weight Management
                </option>
                <option value="Muscle strength">
                    Muscle Strength
                </option>
                <option value="Flexibility">
                    Flexibility
                </option>
                <option value="Improve stamina">
                    Improve Stamina
                </option>
            </select>

            <button type="submit">
                Generate My Fitness Plan
            </button>

        </form>

        <p class="note">
            This application provides general fitness
            information only. It is not a substitute
            for professional medical advice.
        </p>

        <hr>

        <p style="text-align:center">
            <a href="/health">Check API Status</a>
            &nbsp; | &nbsp;
            <a href="/docs">API Documentation</a>
        </p>

    </div>

    </body>
    </html>
    """


# ---------------- GENERATE FITNESS PLAN ----------------

@app.post("/generate", response_class=HTMLResponse)
def generate(
    name: str = Form(...),
    age: int = Form(...),
    goal: str = Form(...)
):

    name = name.strip()
    goal = goal.strip()

    if not name or len(name) > 60:
        return HTMLResponse(
            "<h3>Please enter a valid name.</h3>"
        )

    if age < 13 or age > 100:
        return HTMLResponse(
            "<h3>Please enter a valid age.</h3>"
        )

    prompt = f"""
    You are FitBuddy, a friendly general fitness assistant.

    Create a beginner-friendly fitness plan.

    Name: {name}
    Age: {age}
    Goal: {goal}

    Include:
    1. A simple weekly activity schedule.
    2. Beginner-friendly exercises.
    3. Warm-up and cool-down suggestions.
    4. General balanced food and hydration tips.
    5. Rest and recovery suggestions.

    Important:
    - Use simple English and clear headings.
    - Do not recommend extreme dieting or rapid weight loss.
    - Do not diagnose medical conditions or prescribe medicines.
    - For users under 18, avoid calorie restriction
      and focus on healthy habits and age-appropriate activity.
    - Remind users to consult a healthcare professional
      before starting if they have a medical condition.
    - Stop activity if they feel pain, dizziness,
      or unwell.
    """

    workout = ask_gemini(prompt)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO plans
        (name, age, goal, workout, feedback)
        VALUES (?, ?, ?, ?, ?)
    """, (name, age, goal, workout, ""))

    conn.commit()
    conn.close()

    safe_name = html.escape(name)
    safe_goal = html.escape(goal)
    safe_workout = html.escape(workout)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Your FitBuddy Plan</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #eef4ff;
                padding: 20px;
            }}

            .container {{
                max-width: 700px;
                margin: auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
            }}

            h1 {{
                color: #2356a8;
            }}

            .plan {{
                white-space: pre-wrap;
                line-height: 1.7;
                background: #f6f8fc;
                padding: 20px;
                border-radius: 10px;
            }}

            a {{
                color: #2356a8;
            }}
        </style>
    </head>

    <body>
    <div class="container">

        <h1>Your Fitness Plan</h1>

        <p><b>Name:</b> {safe_name}</p>
        <p><b>Goal:</b> {safe_goal}</p>

        <div class="plan">{safe_workout}</div>

        <hr>

        <h3>Give Feedback</h3>

        <form action="/feedback" method="post">

            <input type="hidden" name="name"
                   value="{safe_name}">

            <textarea name="feedback"
                      placeholder="How can we improve your plan?"
                      required
                      style="width:100%;height:100px;
                      box-sizing:border-box"></textarea>

            <button type="submit"
                    style="padding:12px;margin-top:10px">
                Submit Feedback
            </button>

        </form>

        <p><a href="/">Back to Home</a></p>

    </div>
    </body>
    </html>
    """


# ---------------- FEEDBACK ----------------

@app.post("/feedback", response_class=HTMLResponse)
def feedback(
    name: str = Form(...),
    feedback: str = Form(...)
):

    name = name.strip()
    feedback = feedback.strip()

    if not name or not feedback:
        return HTMLResponse(
            "<h3>Please enter your name and feedback.</h3>"
        )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE plans
        SET feedback = ?
        WHERE id = (
            SELECT id FROM plans
            WHERE name = ?
            ORDER BY id DESC
            LIMIT 1
        )
    """, (feedback, name))

    conn.commit()
    conn.close()

    return HTMLResponse("""
        <h2>Thank you for your feedback!</h2>
        <p>Your feedback has been saved.</p>
        <a href="/">Go to Home</a>
    """)


# ---------------- ADMIN PAGE ----------------

@app.get("/admin", response_class=HTMLResponse)
def admin():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, age, goal, workout, feedback
        FROM plans
        ORDER BY id DESC
    """)

    records = cursor.fetchall()
    conn.close()

    rows = ""

    for record in records:
        rows += f"""
        <tr>
            <td>{html.escape(str(record[0]))}</td>
            <td>{html.escape(str(record[1]))}</td>
            <td>{html.escape(str(record[2]))}</td>
            <td>{html.escape(str(record[3]))}</td>
            <td>
                <pre>{html.escape(str(record[4]))}</pre>
            </td>
            <td>{html.escape(str(record[5]))}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FitBuddy Admin</title>
        <style>
            body {{
                font-family: Arial;
                padding: 20px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
            }}

            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
            }}

            pre {{
                white-space: pre-wrap;
            }}
        </style>
    </head>

    <body>

        <h1>FitBuddy - Saved Plans</h1>

        <table>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Age</th>
                <th>Goal</th>
                <th>Plan</th>
                <th>Feedback</th>
            </tr>

            {rows}
        </table>

        <p><a href="/">Back to Home</a></p>

    </body>
    </html>
    """


# ---------------- HEALTH CHECK ----------------

@app.get("/health")
def health():

    return {
        "status": "running",
        "application": "FitBuddy AI",
        "model": MODEL,
        "api_key_configured": bool(API_KEY)
    }