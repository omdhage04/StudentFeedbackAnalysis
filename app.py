import os
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Custom Modules
from db import get_connection, init_db
from summarizer import generate_final_summary

# Try to import sentiment model, else use placeholder
try:
    from model_utils import predict_sentiment
except ImportError:
    def predict_sentiment(text): return "Neutral"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "master-overwatch-key-998877")

# --- INITIALIZE DATABASE ---
with app.app_context():
    init_db()

# --- SECURITY UTILS ---
def login_required(role=None):
    if "user_id" not in session:
        return False
    if role and session.get("role") != role:
        # Superadmins can access any dashboard (Admin/Teacher/Student) for debugging
        if session.get("role") == "superadmin":
            return True
        return False
    return True

# --- CACHE CONTROL ---
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# --- PUBLIC ROUTES ---

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}_dashboard"))
    return render_template("index.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/register", methods=["POST"])
def register():
    conn = get_connection()
    cur = conn.cursor()
    name = request.form.get("name")
    email = request.form.get("email")
    prn = request.form.get("student_id")
    password = request.form.get("password")
    college_code = request.form.get("college_code")
    role = request.form.get("role", "student")

    hashed_pw = generate_password_hash(password)

    try:
        cur.execute("""
            INSERT INTO users (email, password, role, status, college_code, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (email, hashed_pw, role, college_code, datetime.now().strftime("%Y-%m-%d %H:%M")))
        
        user_id = cur.lastrowid
        if role == "student":
            cur.execute("INSERT INTO students (user_id, full_name, prn_number, college_code) VALUES (?, ?, ?, ?)", (user_id, name, prn, college_code))
        else:
            cur.execute("INSERT INTO teachers (user_id, full_name, college_code) VALUES (?, ?, ?)", (user_id, name, college_code))
            
        conn.commit()
        flash("Registration successful. Pending admin approval.", "success")
        return redirect(url_for("login"))
    except sqlite3.IntegrityError:
        flash("Email or ID already exists.", "error")
    finally:
        conn.close()
    return redirect(url_for("signup"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}_dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        selected_role = request.form.get("role") 
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # --- THE MASTER BYPASS LOGIC ---
            is_superadmin = (user["role"] == "superadmin")
            if not is_superadmin and user["role"] != selected_role:
                flash(f"Unauthorized: Account registered as {user['role'].upper()}.", "error")
                return redirect(url_for("login"))

            if user["status"] != "approved":
                flash("Account pending approval.", "warning")
                return redirect(url_for("login"))
            
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["college_code"] = user["college_code"]
            
            if user["role"] in ["student", "teacher"]:
                conn = get_connection()
                cur = conn.cursor()
                table = "students" if user["role"] == "student" else "teachers"
                cur.execute(f"SELECT id FROM {table} WHERE user_id = ?", (user["id"],))
                profile = cur.fetchone()
                session["profile_id"] = profile["id"] if profile else None
                conn.close()

            return redirect(url_for(f"{user['role']}_dashboard"))
        
        flash("Invalid email or password.", "error")
    return render_template("login.html")

# --- SUPERADMIN SECTION ---

@app.route("/superadmin/dashboard")
def superadmin_dashboard():
    if not login_required("superadmin"): return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    stats = {
        "total_colleges": cur.execute("SELECT COUNT(DISTINCT college_code) FROM users WHERE college_code != 'GLOBAL'").fetchone()[0],
        "total_users": cur.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "total_feedback": cur.execute("SELECT COUNT(*) FROM feedback_responses").fetchone()[0]
    }
    cur.execute("SELECT id, email, college_code, status, created_at FROM users WHERE role='admin'")
    admins = cur.fetchall()
    cur.execute("SELECT feedback, sentiment, college_code, submitted_at FROM feedback_responses ORDER BY id DESC LIMIT 10")
    recent_feedback = cur.fetchall()
    conn.close()
    return render_template("superadmin.html", stats=stats, admins=admins, recent_feedback=recent_feedback)

@app.route("/superadmin/add_admin", methods=["POST"])
def superadmin_add_admin():
    if not login_required("superadmin"): return redirect(url_for("login"))
    email = request.form.get("email")
    password = generate_password_hash(request.form.get("password"))
    college_code = request.form.get("college_code")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (email, password, role, status, college_code, created_at) VALUES (?, ?, 'admin', 'approved', ?, ?)",
                    (email, password, college_code, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        flash(f"Administrator for {college_code} initialized.", "success")
    except: flash("Admin already exists.", "error")
    finally: conn.close()
    return redirect(url_for("superadmin_dashboard"))

# --- ADMIN SECTION ---

@app.route("/admin/dashboard")
def admin_dashboard():
    if not login_required("admin"): return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    cc = session["college_code"]
    
    stats = {
        "total_users": cur.execute("SELECT COUNT(*) FROM users WHERE college_code=?", (cc,)).fetchone()[0],
        "students": cur.execute("SELECT COUNT(*) FROM students WHERE college_code=?", (cc,)).fetchone()[0],
        "teachers": cur.execute("SELECT COUNT(*) FROM teachers WHERE college_code=?", (cc,)).fetchone()[0],
        "responses": cur.execute("SELECT COUNT(*) FROM feedback_responses WHERE college_code=?", (cc,)).fetchone()[0]
    }
    
    pending = cur.execute("""
        SELECT u.id, COALESCE(t.full_name, s.full_name) as name, u.email, u.role 
        FROM users u LEFT JOIN teachers t ON u.id = t.user_id LEFT JOIN students s ON u.id = s.user_id 
        WHERE u.status = 'pending' AND u.college_code = ?
    """, (cc,)).fetchall()
    
    teachers = cur.execute("""
        SELECT t.user_id, t.full_name as name, t.department 
        FROM teachers t JOIN users u ON t.user_id = u.id 
        WHERE t.college_code=? AND u.status='approved'
    """, (cc,)).fetchall()

    all_students = cur.execute("""
        SELECT u.id, s.full_name as name, u.email 
        FROM users u JOIN students s ON u.id = s.user_id 
        WHERE u.college_code = ? AND u.status = 'approved'
    """, (cc,)).fetchall()
    
    forms = cur.execute("""
        SELECT f.id, f.title, f.created_at, COUNT(r.id), t.full_name 
        FROM feedback_forms f JOIN teachers t ON f.teacher_id = t.id 
        LEFT JOIN feedback_responses r ON f.id = r.form_id 
        WHERE f.college_code = ? GROUP BY f.id
    """, (cc,)).fetchall()
    
    conn.close()
    return render_template("admin_dashboard.html", stats=stats, pending_users=pending, 
                           all_teachers=teachers, all_students=all_students, all_forms=forms)

@app.route("/admin/delete_user", methods=["POST"])
def admin_delete_user():
    if not login_required("admin"): return redirect(url_for("login"))
    user_id = request.form.get("user_id")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ? AND college_code = ?", (user_id, session["college_code"]))
    conn.commit()
    conn.close()
    flash("Node purged from network.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_teacher", methods=["POST"])
def admin_delete_teacher():
    return admin_delete_user()

@app.route("/admin/approve_user", methods=["POST"])
def admin_approve_user():
    if not login_required("admin"): return redirect(url_for("login"))
    status = "approved" if request.form.get("action") == "approve" else "rejected"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = ? WHERE id = ? AND college_code = ?", (status, request.form.get("user_id"), session["college_code"]))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/add_teacher", methods=["POST"])
def admin_add_teacher():
    if not login_required("admin"): return redirect(url_for("login"))
    hashed_pw = generate_password_hash(request.form.get("password"))
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (email, password, role, status, college_code, created_at) VALUES (?, ?, 'teacher', 'approved', ?, ?)",
                    (request.form.get("email"), hashed_pw, session["college_code"], datetime.now().strftime("%Y-%m-%d %H:%M")))
        cur.execute("INSERT INTO teachers (user_id, full_name, college_code, department) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, request.form.get("name"), session["college_code"], request.form.get("department")))
        conn.commit()
        flash("Faculty account created.", "success")
    except: flash("Error creating faculty node.", "error")
    finally: conn.close()
    return redirect(url_for("admin_dashboard"))

# --- TEACHER SECTION ---

@app.route("/teacher/dashboard")
def teacher_dashboard():
    if not login_required("teacher"): return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM teachers WHERE user_id = ?", (session["user_id"],))
    teacher = cur.fetchone()
    pending = cur.execute("""
        SELECT u.id, s.full_name, s.prn_number FROM users u 
        JOIN students s ON u.id = s.user_id 
        WHERE u.status = 'pending' AND u.college_code = ?
    """, (session["college_code"],)).fetchall()
    my_students = cur.execute("""
        SELECT full_name, prn_number, mobile_no FROM students 
        WHERE college_code = ? AND user_id IN (SELECT id FROM users WHERE status='approved')
    """, (session["college_code"],)).fetchall()
    forms = cur.execute("""
        SELECT f.id, f.title, f.created_at, COUNT(r.id) as r_count 
        FROM feedback_forms f LEFT JOIN feedback_responses r ON f.id = r.form_id 
        WHERE f.teacher_id = ? GROUP BY f.id
    """, (session["profile_id"],)).fetchall()
    conn.close()
    return render_template("teacher_dashboard.html", teacher=teacher, pending_students=pending, my_students=my_students, forms=forms)

@app.route("/teacher/create_form", methods=["POST"])
def create_form():
    if not login_required("teacher"): return redirect(url_for("login"))
    title = request.form.get("title")
    if title:
        conn = get_connection()
        cur = conn.cursor()
        f_id = str(uuid.uuid4())[:8]
        cur.execute("INSERT INTO feedback_forms (id, title, college_code, created_at, teacher_id) VALUES (?, ?, ?, ?, ?)",
                    (f_id, title, session["college_code"], datetime.now().strftime("%Y-%m-%d"), session["profile_id"]))
        conn.commit()
        conn.close()
        flash("Feedback session deployed.", "success")
    return redirect(url_for("teacher_dashboard"))

@app.route("/approve_student", methods=["POST"])
def approve_student():
    if not login_required("teacher"): return redirect(url_for("login"))
    u_id = request.form.get("user_id")
    status = "approved" if request.form.get("action") == "approve" else "rejected"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = ? WHERE id = ? AND college_code = ?", (status, u_id, session["college_code"]))
    conn.commit()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

# --- STUDENT SECTION ---

@app.route("/student/dashboard", methods=["GET", "POST"])
def student_dashboard():
    if not login_required("student"): return redirect(url_for("login"))
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_profile":
            cur.execute("""
                UPDATE students SET mobile_no=?, department=?, class_name=?, 
                academic_year=?, teacher_name=?, hod_name=? WHERE user_id=?
            """, (request.form.get("mobile"), request.form.get("dept"), request.form.get("class"),
                  request.form.get("year"), request.form.get("teacher"), request.form.get("hod"), session["user_id"]))
            conn.commit()
            flash("Metadata synchronized.", "success")
        elif action == "submit_feedback":
            fb = request.form.get("feedback")
            cur.execute("""
                INSERT INTO feedback_responses (form_id, student_id, college_code, feedback, sentiment, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (request.form.get("form_id"), session["profile_id"], session["college_code"], 
                  fb, predict_sentiment(fb), datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            flash("Signal transmitted.", "success")

    cur.execute("SELECT * FROM students WHERE user_id = ?", (session["user_id"],))
    student = cur.fetchone()
    fields = [student['mobile_no'], student['department'], student['class_name'], student['academic_year'], student['teacher_name'], student['hod_name']]
    progress = int((sum(1 for f in fields if f and str(f).strip()) / 6) * 100)
    forms = cur.execute("SELECT id, title FROM feedback_forms WHERE college_code = ?", (session["college_code"],)).fetchall()
    conn.close()
    return render_template("student_dashboard.html", student=student, progress=progress, forms=forms)

# --- ANALYTICS (AI CACHING ENABLED) ---

@app.route("/analytics/<form_id>")
def view_analytics(form_id):
    if "user_id" not in session: return redirect(url_for("login"))
    
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Fetch Form & Cached Summary
    cur.execute("SELECT title, ai_summary FROM feedback_forms WHERE id = ?", (form_id,))
    form = cur.fetchone()
    
    if not form:
        conn.close()
        return "Not Found", 404

    # 2. Fetch Responses
    cur.execute("SELECT feedback, sentiment FROM feedback_responses WHERE form_id = ?", (form_id,))
    responses = cur.fetchall()
    
    # 3. Intelligent AI Summary Caching
    ai_report = form['ai_summary']
    
    if not ai_report and len(responses) > 0:
        # Convert DB result to plain list for summarizer
        feedback_list = [r['feedback'] for r in responses]
        
        # Slow part (only once)
        ai_report = generate_final_summary(feedback_list)
        
        # Cache the result
        cur.execute("UPDATE feedback_forms SET ai_summary = ? WHERE id = ?", (ai_report, form_id))
        conn.commit()
    elif not ai_report:
        ai_report = "Insufficient feedback signals to generate intelligence summary."

    conn.close()
    return render_template("analytics.html", title=form["title"], responses=responses, ai_summary=ai_report)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)