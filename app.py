from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, hashlib

app = Flask(__name__)
app.secret_key = "vvitu_secret_2024"

DB = os.path.join(os.path.dirname(__file__), "vvitu.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, roll TEXT UNIQUE NOT NULL,
        route TEXT, bus_number TEXT, total_fee REAL DEFAULT 0,
        paid_fee REAL DEFAULT 0, depart_stop TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, bus_number TEXT, depart_stop TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_number TEXT, route_name TEXT, bus_number TEXT,
        timing TEXT, stops TEXT
    )""")
    # Seed data
    c.execute("SELECT COUNT(*) FROM routes")
    if c.fetchone()[0] == 0:
        routes = [
            ("R01","Vijayawada - VVITU","BUS-101","7:30 AM","Vijayawada → Gudivada → Kaikaluru → VVITU"),
            ("R02","Machilipatnam - VVITU","BUS-102","7:00 AM","Machilipatnam → Bantumilli → Kaikaluru → VVITU"),
            ("R03","Eluru - VVITU","BUS-103","6:45 AM","Eluru → Bhimavaram → Tanuku → VVITU"),
            ("R04","Gudivada - VVITU","BUS-104","8:00 AM","Gudivada → Pedana → Kaikaluru → VVITU"),
            ("R05","Kakinada - VVITU","BUS-105","6:30 AM","Kakinada → Amalapuram → Narsapur → VVITU"),
        ]
        c.executemany("INSERT INTO routes (route_number,route_name,bus_number,timing,stops) VALUES (?,?,?,?,?)", routes)

    c.execute("SELECT COUNT(*) FROM students")
    if c.fetchone()[0] == 0:
        students = [
            ("Ravi Kumar","22A91A0501","R01","BUS-101",12000,8000,"Vijayawada"),
            ("Lakshmi Devi","22A91A0502","R02","BUS-102",12000,12000,"Machilipatnam"),
            ("Arjun Rao","22A91A0503","R03","BUS-103",12000,4000,"Eluru"),
            ("Priya Sharma","22A91A0504","R04","BUS-104",12000,0,"Gudivada"),
            ("Suresh Babu","22A91A0505","R05","BUS-105",12000,12000,"Kakinada"),
            ("Meena Kumari","22A91A0506","R01","BUS-101",12000,6000,"Vijayawada"),
        ]
        c.executemany("INSERT INTO students (name,roll,route,bus_number,total_fee,paid_fee,depart_stop) VALUES (?,?,?,?,?,?,?)", students)

    conn.commit()
    conn.close()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    student = session.get("student")
    staff   = session.get("staff")
    return render_template("index.html", student=student, staff=staff)

@app.route("/bus-routes")
def bus_routes():
    conn = get_db(); rows = conn.execute("SELECT * FROM routes").fetchall(); conn.close()
    return render_template("bus_routes.html", routes=rows,
                           student=session.get("student"), staff=session.get("staff"))

@app.route("/live-tracker")
def live_tracker():
    return render_template("live_tracker.html",
                           student=session.get("student"), staff=session.get("staff"))

# ── Student Login ──────────────────────────────────────────────────────────────
@app.route("/student-login", methods=["GET","POST"])
def student_login():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        roll = request.form.get("roll","").strip()
        conn = get_db()
        s = conn.execute("SELECT * FROM students WHERE roll=? AND LOWER(name)=LOWER(?)",(roll,name)).fetchone()
        conn.close()
        if s:
            session["student"] = dict(s)
            return redirect(url_for("student_dashboard"))
        flash("Student not found. Check your name and roll number.","error")
    return render_template("student_login.html")

@app.route("/student-dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect(url_for("student_login"))
    s = session["student"]
    remaining = s["total_fee"] - s["paid_fee"]
    status = "Paid" if remaining <= 0 else "Pending"
    conn = get_db()
    route = conn.execute("SELECT * FROM routes WHERE route_number=?",(s["route"],)).fetchone()
    conn.close()
    return render_template("student_dashboard.html", s=s, remaining=remaining, status=status, route=route)

# ── Staff Login / Register ─────────────────────────────────────────────────────
@app.route("/staff-login", methods=["GET","POST"])
def staff_login():
    return render_template("staff_login.html")

@app.route("/staff-login/existing", methods=["POST"])
def staff_existing():
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    conn = get_db()
    st = conn.execute("SELECT * FROM staff WHERE username=? AND password=?",(username, hash_pw(password))).fetchone()
    conn.close()
    if st:
        session["staff"] = dict(st)
        return redirect(url_for("admin_panel"))
    flash("Invalid credentials. Please try again.","error")
    return redirect(url_for("staff_login"))

@app.route("/staff-login/register", methods=["POST"])
def staff_register():
    name     = request.form.get("name","").strip()
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    bus      = request.form.get("bus_number","").strip()
    depart   = request.form.get("depart_stop","").strip()
    if not all([name, username, password]):
        flash("All fields are required.","error")
        return redirect(url_for("staff_login"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO staff (name,username,password,bus_number,depart_stop) VALUES (?,?,?,?,?)",
                     (name, username, hash_pw(password), bus, depart))
        conn.commit()
        st = conn.execute("SELECT * FROM staff WHERE username=?",(username,)).fetchone()
        session["staff"] = dict(st)
        conn.close()
        return render_template("staff_welcome.html", staff=dict(st))
    except sqlite3.IntegrityError:
        conn.close()
        flash("Username already exists. Please choose another.","error")
        return redirect(url_for("staff_login"))

# ── Admin Panel ────────────────────────────────────────────────────────────────
@app.route("/admin")
def admin_panel():
    if "staff" not in session:
        return redirect(url_for("staff_login"))
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    routes   = conn.execute("SELECT * FROM routes").fetchall()
    conn.close()
    return render_template("admin.html", students=students, routes=routes, staff=session["staff"])

@app.route("/admin/add-student", methods=["POST"])
def add_student():
    if "staff" not in session: return redirect(url_for("staff_login"))
    d = request.form
    conn = get_db()
    try:
        conn.execute("INSERT INTO students (name,roll,route,bus_number,total_fee,paid_fee,depart_stop) VALUES (?,?,?,?,?,?,?)",
            (d["name"],d["roll"],d["route"],d["bus_number"],float(d["total_fee"]),float(d["paid_fee"]),d["depart_stop"]))
        conn.commit()
        flash("Student added successfully!","success")
    except sqlite3.IntegrityError:
        flash("Roll number already exists.","error")
    finally: conn.close()
    return redirect(url_for("admin_panel"))

@app.route("/admin/update-fee", methods=["POST"])
def update_fee():
    if "staff" not in session: return redirect(url_for("staff_login"))
    roll     = request.form.get("roll")
    paid_fee = float(request.form.get("paid_fee",0))
    conn = get_db()
    conn.execute("UPDATE students SET paid_fee=? WHERE roll=?",(paid_fee, roll))
    conn.commit(); conn.close()
    flash("Fee updated successfully!","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/add-route", methods=["POST"])
def add_route():
    if "staff" not in session: return redirect(url_for("staff_login"))
    d = request.form
    conn = get_db()
    conn.execute("INSERT INTO routes (route_number,route_name,bus_number,timing,stops) VALUES (?,?,?,?,?)",
        (d["route_number"],d["route_name"],d["bus_number"],d["timing"],d["stops"]))
    conn.commit(); conn.close()
    flash("Route added successfully!","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete-student/<int:sid>")
def delete_student(sid):
    if "staff" not in session: return redirect(url_for("staff_login"))
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?",(sid,))
    conn.commit(); conn.close()
    return redirect(url_for("admin_panel"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ── API ────────────────────────────────────────────────────────────────────────
@app.route("/api/routes")
def api_routes():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM routes").fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5050)
