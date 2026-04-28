from flask import Flask, render_template, request, redirect, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
import os
import random
import PyPDF2
import pytesseract
from PIL import Image
import re


def get_db():
    return sqlite3.connect("database.db")

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024   # 5 MB limit

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


from flask import request

@app.errorhandler(413)
def file_too_large(e):
    return render_template("prediction.html", error="❌ File too large")


# ---------- TEXT EXTRACTION ----------
def extract_text(path):
    text = ""
    if path.endswith(".pdf"):
        with open(path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
    else:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
    return text


# ---------- SUMMARY ----------
def generate_summary(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    important = []

    keywords = [
        "result", "level", "value", "test", "positive", "negative",
        "normal", "abnormal", "high", "low", "hemoglobin", "glucose",
        "cholesterol", "pressure", "rate"
    ]

    for line in lines:
        for word in keywords:
            if word.lower() in line.lower():
                clean_line = re.sub(r'[^a-zA-Z0-9:/.%\s-]', '', line)
                important.append(clean_line)
                break

    important = list(dict.fromkeys(important))
    return important[:8] if important else ["No important data found in report"]


# ---------- RISK ----------
def calculate_risk(metrics):
    risk = 0

    hr = metrics["Heart Rate"]
    bp = metrics["Blood Pressure"]
    chol = metrics["Cholesterol"]

    if hr > 100:
        risk += 30
    elif hr > 80:
        risk += 15

    if bp > 140:
        risk += 30
    elif bp > 120:
        risk += 15

    if chol > 240:
        risk += 40
    elif chol > 200:
        risk += 20

    return min(risk, 100)


def risk_level(score):
    if score < 30:
        return "Low"
    elif score < 70:
        return "Medium"
    else:
        return "High"


# ---------- DATABASE ----------
conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS patients(
    name TEXT PRIMARY KEY,
    phone TEXT,
    dob TEXT,
    report TEXT,
    summary TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS appointments(
    name TEXT,
    date TEXT,
    time TEXT,
    status TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

conn.commit()
conn.close()


# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        # 🔥 ONLY check username
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user:
            db_password = user[1]
            db_role = user[2]

            # 🔥 Check password + role manually
            if check_password_hash(db_password, password) and role == db_role:
                session["username"] = user[0]
                session["role"] = db_role

                return redirect("/patient" if db_role=="patient" else "/doctor")

        return "<h3>Invalid Login (Check role / username / password)</h3>"

    return render_template("login.html")


# ---------- SIGNUP ----------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        username = request.form["username"]
        password = request.form["password"]
        phone = request.form.get("phone","")
        dob = request.form.get("dob","")
        role = request.form["role"]


        print("USERNAME:", username)
        print("PHONE:", phone)
        print("DOB:",dob)
        print("ROLE:", role)

        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        if cur.fetchone():
            return "<h3>Username already exists</h3>"

        hashed = generate_password_hash(password)

        cur.execute("INSERT INTO users VALUES (?,?,?)",
                    (username, hashed, role))

        if role == "patient":
            cur.execute("INSERT INTO patients(name,  phone, dob, report, summary) VALUES(?,?,?,?,?)",
                        (username,  phone, dob, "", "No reports yet"))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- PATIENT ----------

@app.route("/patient")
def patient():
    if "username" not in session:
        return redirect("/login")
    
    update_completed_appointments()

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # ✅ Only phone is selected
    cur.execute("SELECT phone, dob FROM patients WHERE name=?", (session["username"],))
    info = cur.fetchone()

    

    cur.execute("""
        SELECT date, time, status 
        FROM appointments 
        WHERE name=? 
        ORDER BY rowid DESC 
        LIMIT 1
    """, (session["username"],))
    
    result = cur.fetchone()
    conn.close()

    return render_template("patient_dashboard.html",
                           latest_date=result[0] if result else "-",
                           latest_time=result[1] if result else "-",
                           status=result[2] if result else "No Appointments",
                           phone=info[0] if info else "-",
                            dob=info[1] if info else "-" 
                           )


def update_completed_appointments():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT name, date, time, status FROM appointments WHERE status='Approved'")
    rows = cur.fetchall()

    now = datetime.now()

    for name, date, time, status in rows:
        if time:
            try:
                # handle both HH:MM and HH:MM:SS
                if len(time) == 5:
                    time = time + ":00"

                appt_datetime = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")

                if appt_datetime <= now:
                    cur.execute("""
                        UPDATE appointments
                        SET status='Completed'
                        WHERE name=? AND date=? AND time=? AND status='Approved'
                    """, (name, date, time))   # ✅ FIXED HERE

            except Exception as e:
                print("ERROR:", e)

    conn.commit()
    conn.close()



# ---------- DOCTOR ----------
@app.route("/doctor")
def doctor():
    if "username" not in session or session["role"] != "doctor":
        return redirect("/login")

    update_completed_appointments()   # ✅ ADD THIS LINE

    return render_template("doctor_dashboard.html")


# ---------- PATIENT LIST (DOCTOR SIDE) ----------
@app.route("/patients")
def patients():
    if "username" not in session or session["role"] != "doctor":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT name FROM patients")
    data = cur.fetchall()

    conn.close()
    return render_template("patients.html", data=data)


# ---------- PATIENT DETAILS ----------
@app.route("/patient_details/<name>")
def patient_details(name):
    if "username" not in session or session["role"] != "doctor":
        return redirect("/login")

    update_completed_appointments()  # ✅ keep status correct

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # patient data
    cur.execute("SELECT * FROM patients WHERE name=?", (name,))
    patient = cur.fetchone()

    # appointments
    cur.execute("SELECT date, time, status FROM appointments WHERE name=?", (name,))
    appointments = cur.fetchall()
    print("PATIENT DATA:", patient)

    conn.close()

    return render_template("patient_details.html",
                           patient=patient,
                           appointments=appointments)


# ---------- REPORT ----------
@app.route("/prediction", methods=["GET","POST"])
def prediction():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = session["username"]
        file = request.files["report"]
        filename = file.filename

        # 🔥 Check empty file
        if filename == "":
            return render_template("prediction.html",
                                   error="❌ No file selected")

        # 🔥 File type validation
        allowed_extensions = ["pdf", "png", "jpg", "jpeg"]
        ext = filename.split(".")[-1].lower()

        if ext not in allowed_extensions:
            return render_template("prediction.html",
                                   error="❌ Only PDF & Image files allowed")

        # ✅ Continue normally
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

        text = extract_text(path)
        summary = generate_summary(text)

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM patients WHERE name=?", (name,))
        existing = cur.fetchone()

        if existing:
            cur.execute("UPDATE patients SET report=?, summary=? WHERE name=?",
                        (filename, "\n".join(summary), name))
        else:
            cur.execute("INSERT INTO patients(name, report, summary) VALUES(?,?,?)",
                        (name, filename, "\n".join(summary)))

        conn.commit()
        conn.close()
        # ---------- EXTRACT METRICS FROM REPORT ----------
        def extract_metrics(text):
            metrics = {}

            hr_match = re.search(r'Heart Rate[:\s]+(\d+)', text, re.IGNORECASE)
            metrics["Heart Rate"] = int(hr_match.group(1)) if hr_match else 0

            bp_match = re.search(r'Blood Pressure[:\s]+(\d+)', text, re.IGNORECASE)
            metrics["Blood Pressure"] = int(bp_match.group(1)) if bp_match else 0

            chol_match = re.search(r'Cholesterol[:\s]+(\d+)', text, re.IGNORECASE)
            metrics["Cholesterol"] = int(chol_match.group(1)) if chol_match else 0

            return metrics

        metrics = extract_metrics(text)
        metrics["Risk Score"] = calculate_risk(metrics)

        

        return render_template("report_result.html",
                               name=name,
                               filename=filename,
                               metrics=metrics,
                               level=risk_level(metrics["Risk Score"]),
                               summary=summary)

    return render_template("prediction.html")



# ---------- ADD SUMMARY ----------
@app.route("/add_summary", methods=["POST"])
def add_summary():
    if "username" not in session or session["role"] != "doctor":
        return redirect("/login")
    update_completed_appointments()

    name = request.form["name"]
    summary = request.form["summary"]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE patients
        SET summary=?
        WHERE name=?
    """, (summary, name))

    conn.commit()
    conn.close()

    return redirect("/view_reports")




# ---------- VIEW REPORTS ----------
@app.route("/view_reports")
def view_reports():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients")
    data = cur.fetchall()
    conn.close()
    return render_template("view_reports.html", data=data)


# ---------- APPOINTMENT ----------
from datetime import datetime, time

@app.route("/appointment", methods=["GET","POST"])
def appointment():
    if "username" not in session or session["role"] != "patient":
        return redirect("/login")

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.time()

    if request.method == "POST":
        selected_date = request.form["date"]

        if selected_date < today:
            return render_template("appointment.html", today=today,
                                   error="❌ Cannot book past dates")

        if selected_date == today and current_time >= time(18, 0):
            return render_template("appointment.html", today=today,
                                   error="❌ Today's booking is closed after 6 PM")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("INSERT INTO appointments VALUES (?,?,?,?)",
                    (session["username"], selected_date, "", "Pending"))

        conn.commit()
        conn.close()

        return redirect("/my_appointments")

    return render_template("appointment.html", today=today)


@app.route("/my_appointments")
def my_appointments():
    if "username" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM appointments WHERE name=?", (session["username"],))
    data = cur.fetchall()

    conn.close()
    return render_template("my_appointments.html", data=data)


@app.route("/appointments")
def appointments():
    if "username" not in session or session["role"] != "doctor":
        return redirect("/login")
    update_completed_appointments()

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM appointments WHERE date IS NOT NULL AND date != ''")
    data = cur.fetchall()

    conn.close()
    return render_template("view_appointments.html", data=data)


@app.route("/update_appointment", methods=["POST"])
def update_appointment():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    time = request.form["time"]
    if len(time) == 5:  # if HH:MM
        time = time + ":00"

    cur.execute("""
        UPDATE appointments
        SET time=?, status=?
        WHERE name=? AND date=?
    """, (time, request.form["status"],
          request.form["name"], request.form["date"]))

    conn.commit()
    conn.close()

    return redirect("/appointments")


@app.route("/appointment_details/<name>/<date>")
def appointment_details(name, date):
    if "username" not in session:
        return redirect("/login")

    # ✅ VERY IMPORTANT LINE (YOU MISSED THIS)
    update_completed_appointments()

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM appointments WHERE name=? AND date=?", (name, date))
    data = cur.fetchone()

    conn.close()

    return render_template("appointment_details.html", data=data)



# ---------- MY REPORTS ----------
@app.route("/my_reports")
def my_reports():
    if "username" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM patients WHERE name=?", (session["username"],))
    data = cur.fetchall()

    conn.close()
    return render_template("my_reports.html", data=data)


# ---------- FILE ----------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)