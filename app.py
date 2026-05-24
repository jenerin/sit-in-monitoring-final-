from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import io
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = "ccs_sitin_secret_key_2025"

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "images", "avatars")
DB_PATH    = os.path.join(os.path.dirname(__file__), "sitin_monitor.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Database Helpers ─────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_sessions_feedback_column(conn)
    return conn

def ensure_sessions_feedback_column(conn):
    cursor = conn.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    if "feedback" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN feedback TEXT")
        conn.commit()

def dict_from_row(row):
    return dict(row) if row else None

def get_initials(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()

app.jinja_env.globals["get_initials"] = get_initials

# ─── Public Routes ───────────────────────────────────────────────────────────

@app.route("/")
def landing():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY reward_points DESC").fetchall()
    
    # ─── ADD THIS: Fetch approved testimonials to show on landing page ───
    testimonials_data = conn.execute("SELECT * FROM testimonials WHERE approved = 1 ORDER BY date DESC").fetchall()
    
    conn.close()
    
    # Build unified leaderboard entries
    leaderboard = []
    for s in students[:10]:
        leaderboard.append({
            "student_id": s["id"],
            "student_name": s["name"],
            "course": s["course"],
            "reward_points": s["reward_points"],
            "total_sessions": s["sit_in_count"],
        })
    top3 = leaderboard[:3]
    rest = leaderboard[3:10]
    
    # ─── UPDATED: Added approved_testimonials to render_template ───
    return render_template("landing.html", top3=top3, rest=rest, approved_testimonials=[dict(t) for t in testimonials_data])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "").strip()

        # Admin check
        if student_id == "admin" and password == "admin123":
            session["user"] = {"id": "admin", "name": "Administrator", "role": "admin"}
            return redirect(url_for("admin_dashboard"))

        conn = get_db()
        student = conn.execute("SELECT * FROM students WHERE id = ? AND password = ?", (student_id, password)).fetchone()
        conn.close()
        
        if student:
            session["user"] = {
                "id": student["id"],
                "name": student["name"],
                "course": student["course"],
                "year": student["year"],
                "role": "student"
            }
            return redirect(url_for("student_dashboard"))
        flash("Invalid credentials. Please try again.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        course = request.form.get("course", "").strip()
        year = request.form.get("year", "1").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        
        conn = get_db()
        existing = conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
        if existing:
            conn.close()
            flash("Student ID already registered.", "error")
            return render_template("register.html")

        conn.execute('''
            INSERT INTO students (id, name, course, year, email, password, sessions_left, reward_points, 
                                  sit_in_count, active_session, current_lab, current_subject, login_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, name, course, int(year), email, password, 30, 0, 0, 0, None, None, None))
        conn.commit()
        conn.close()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# ─── Student Routes ──────────────────────────────────────────────────────────

def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or session["user"].get("role") != "student":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def add_notification(student_id, message):
    """Helper to add a notification for a student."""
    conn = get_db()
    conn.execute('''
        INSERT INTO notifications (student_id, message, date, read)
        VALUES (?, ?, ?, ?)
    ''', (student_id, message, datetime.now().strftime("%Y-%m-%d"), 0))
    conn.commit()
    conn.close()


def get_unread_count(student_id):
    """Return count of unread notifications for a student."""
    conn = get_db()
    count = conn.execute('''
        SELECT COUNT(*) as count FROM notifications 
        WHERE student_id = ? AND read = 0
    ''', (student_id,)).fetchone()
    conn.close()
    return count["count"] if count else 0

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user"]["id"],)).fetchone()
    
    announcements = conn.execute("SELECT * FROM announcements ORDER BY date DESC").fetchall()
    if not announcements:
        announcements = [
            {"title": "Welcome to CCS Lab Monitoring System", "body": "The new sit-in monitoring system is now live. Please register...", "date": "2025-01-18"},
            {"title": "Lab Schedule Update", "body": "Lab 3 will be under maintenance this Friday...", "date": "2025-01-12"}
        ]
    
    unread_count = get_unread_count(session["user"]["id"])
    
    # Find active session for this student
    active_session = conn.execute('''
        SELECT * FROM sessions 
        WHERE student_id = ? AND status = "ACTIVE"
    ''', (session["user"]["id"],)).fetchone()
    
    # Calculate sit-in summary statistics
    my_sessions = conn.execute('''
        SELECT * FROM sessions 
        WHERE student_id = ? AND status = "DONE"
    ''', (session["user"]["id"],)).fetchall()
    
    total_sessions = len(my_sessions)
    total_hours = 0
    longest_duration = 0
    durations = []
    
    for s in my_sessions:
        if s["time_in"] and s["time_out"]:
            try:
                time_in = datetime.strptime(s["time_in"], "%H:%M")
                time_out = datetime.strptime(s["time_out"], "%H:%M")
                duration = (time_out - time_in).total_seconds() / 3600
                if duration > 0:
                    total_hours += duration
                    durations.append(duration)
                    if duration > longest_duration:
                        longest_duration = duration
            except:
                pass
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    sitin_summary = {
        "total_hours": round(total_hours, 2),
        "total_sessions": total_sessions,
        "avg_duration": round(avg_duration, 2),
        "longest_duration": round(longest_duration, 2)
    }
    
    conn.close()
    
    return render_template("student/dashboard.html", student=dict(student), announcements=[dict(a) for a in announcements][:5], unread_count=unread_count, active_session=dict(active_session) if active_session else None, sitin_summary=sitin_summary, my_sessions=[dict(s) for s in my_sessions])

@app.route("/student/edit-profile", methods=["GET", "POST"])
@student_required
def student_edit_profile():
    conn = get_db()
    db_student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user"]["id"],)).fetchone()
    
    if not db_student:
        conn.close()
        flash("Student profile not found.", "error")
        return redirect(url_for("student_dashboard"))
        
    student = dict(db_student)
    
    if request.method == "POST":
        name = request.form.get("name", student["name"]).strip()
        course = request.form.get("course", student["course"]).strip()
        year = int(request.form.get("year", student["year"]))
        email = request.form.get("email", student.get("email", "")).strip()
        new_pass = request.form.get("new_password", "").strip()
        
        # Handle photo upload
        avatar = student.get("avatar")
        photo = request.files.get("photo")
        if photo and photo.filename and allowed_file(photo.filename):
            ext = photo.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{student['id']}.{ext}")
            photo.save(os.path.join(UPLOAD_DIR, filename))
            avatar = f"images/avatars/{filename}"
        
        # Update student
        if new_pass:
            conn.execute('''
                UPDATE students SET name=?, course=?, year=?, email=?, password=?, avatar=?
                WHERE id=?
            ''', (name, course, year, email, new_pass, avatar, session["user"]["id"]))
        else:
            conn.execute('''
                UPDATE students SET name=?, course=?, year=?, email=?, avatar=?
                WHERE id=?
            ''', (name, course, year, email, avatar, session["user"]["id"]))
        
        conn.commit()
        
        # Refresh student record for session and rendering
        db_student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user"]["id"],)).fetchone()
        student = dict(db_student)
        session["user"]["name"] = student["name"]
        conn.close()
        
        flash("Profile updated successfully.", "success")
        return redirect(url_for("student_edit_profile"))
    
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/edit_profile.html", student=student, unread_count=unread_count)

@app.route("/student/history")
@student_required
def student_history():
    conn = get_db()
    my_sessions = conn.execute('''
        SELECT * FROM sessions WHERE student_id = ? ORDER BY date DESC, time_in DESC
    ''', (session["user"]["id"],)).fetchall()
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/history.html", sessions=[dict(s) for s in my_sessions], unread_count=unread_count)

@app.route("/student/history/feedback", methods=["POST"])
@student_required
def student_history_feedback():
    session_id = request.form.get("session_id")
    feedback = request.form.get("feedback", "").strip()
    if not session_id:
        flash("Invalid session selected.", "error")
        return redirect(url_for("student_history"))

    conn = get_db()
    existing = conn.execute("SELECT id FROM sessions WHERE id = ? AND student_id = ?", (session_id, session["user"]["id"])).fetchone()
    if not existing:
        conn.close()
        flash("Could not find the selected sit-in record.", "error")
        return redirect(url_for("student_history"))

    conn.execute("UPDATE sessions SET feedback = ? WHERE id = ?", (feedback, session_id))
    conn.commit()
    conn.close()

    flash("Your feedback has been saved.", "success")
    return redirect(url_for("student_history"))

@app.route("/student/reservation", methods=["GET", "POST"])
@student_required
def student_reservation():
    conn = get_db()
    my_reservations = conn.execute('''
        SELECT * FROM reservations WHERE student_id = ?
    ''', (session["user"]["id"],)).fetchall()
    
    all_reservations = conn.execute("SELECT * FROM reservations").fetchall()

    # Load admin-set PC status so the student map reflects real availability
    pc_status_rows = conn.execute("SELECT * FROM pc_status").fetchall()
    pc_status = {}
    for row in pc_status_rows:
        if row["lab"] not in pc_status:
            pc_status[row["lab"]] = {}
        pc_status[row["lab"]][row["pc_number"]] = row["status"]
    
    labs = ["Lab 1", "Lab 2", "Lab 3"]
    for lab in labs:
        if lab not in pc_status:
            pc_status[lab] = {}
        for i in range(1, 31):
            if str(i) not in pc_status[lab]:
                pc_status[lab][str(i)] = "available"

    if request.method == "POST":
        pc_number = request.form.get("pc_number", "").strip()
        if not pc_number:
            conn.close()
            flash("Please select a PC from the map.", "error")
            return render_template("student/reservation.html",
                                   reservations=[dict(r) for r in my_reservations],
                                   all_reservations=[dict(r) for r in all_reservations],
                                   pc_status=pc_status)
        
        # Get next ID
        max_id = conn.execute("SELECT MAX(id) as max_id FROM reservations").fetchone()
        new_id = (max_id["max_id"] or 0) + 1
        
        conn.execute('''
            INSERT INTO reservations (id, student_id, student_name, lab, pc_number, date, time_slot, subject, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, session["user"]["id"], session["user"]["name"], request.form.get("lab"),
              int(pc_number), request.form.get("date"), request.form.get("time_slot"),
              request.form.get("subject"), "PENDING"))
        conn.commit()
        conn.close()
        
        flash("Reservation submitted successfully.", "success")
        return redirect(url_for("student_reservation"))
    
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/reservation.html",
                           reservations=[dict(r) for r in my_reservations],
                           all_reservations=[dict(r) for r in all_reservations],
                           pc_status=pc_status,
                           unread_count=unread_count)

@app.route("/student/software")
@student_required
def student_software():
    conn = get_db()
    software_apps = conn.execute("SELECT * FROM software_apps ORDER BY lab, name").fetchall()
    labs_rows = conn.execute("SELECT DISTINCT lab FROM software_apps WHERE lab IS NOT NULL AND lab != ''").fetchall()
    conn.close()

    existing_labs = sorted({row["lab"] for row in labs_rows if row["lab"]})
    labs = ["All Labs"] + [lab for lab in existing_labs if lab != "All Labs"]
    selected_lab = request.args.get("lab", "All Labs")

    software_apps = [dict(a) for a in software_apps]
    if selected_lab and selected_lab != "All Labs":
        software_apps = [app for app in software_apps if app["lab"] == selected_lab]

    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/software.html",
                           software_apps=software_apps,
                           labs=labs,
                           selected_lab=selected_lab,
                           unread_count=unread_count)

@app.route("/student/software/install/<int:app_id>", methods=["POST"])
@student_required
def student_software_install(app_id):
    conn = get_db()
    app_item = conn.execute("SELECT * FROM software_apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not app_item:
        flash("Software item not found.", "error")
        return redirect(url_for("student_software"))

    add_notification(session["user"]["id"], f"Install request submitted for {app_item['name']}.")
    flash(f"Install request for {app_item['name']} submitted.", "success")
    selected_lab = request.form.get("lab", "All Labs")
    return redirect(url_for("student_software", lab=selected_lab))

@app.route("/student/announcements")
@student_required
def student_announcements():
    conn = get_db()
    announcements = conn.execute("SELECT * FROM announcements ORDER BY date DESC").fetchall()
    if not announcements:
        announcements = [
            {"title": "Welcome to CCS Lab Monitoring System", "body": "The new sit-in monitoring system is now live. Please register and explore the features.", "date": "2025-01-18"},
            {"title": "Lab Schedule Update", "body": "Lab 3 will be under maintenance this Friday. Please use Lab 1 or Lab 2.", "date": "2025-01-12"}
        ]
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/announcements.html", announcements=[dict(a) for a in announcements], unread_count=unread_count)

@app.route("/student/rewards")
@student_required
def student_rewards():
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user"]["id"],)).fetchone()
    leaderboard = conn.execute("SELECT * FROM students ORDER BY reward_points DESC LIMIT 10").fetchall()
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/rewards.html", student=dict(student), leaderboard=[dict(s) for s in leaderboard], unread_count=unread_count)

@app.route("/student/notifications")
@student_required
def student_notifications():
    conn = get_db()
    my_notifs = conn.execute('''
        SELECT * FROM notifications WHERE student_id = ? ORDER BY date DESC
    ''', (session["user"]["id"],)).fetchall()
    
    # Mark all as read
    conn.execute('''
        UPDATE notifications SET read = 1 WHERE student_id = ?
    ''', (session["user"]["id"],))
    conn.commit()
    conn.close()
    
    return render_template("student/notifications.html", notifications=[dict(n) for n in my_notifs])


@app.route("/student/rules")
@student_required
def student_rules():
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/rules.html", unread_count=unread_count)

@app.route("/student/sessions")
@student_required
def student_sessions():
    conn = get_db()
    my_sessions = conn.execute('''
        SELECT * FROM sessions WHERE student_id = ?
    ''', (session["user"]["id"],)).fetchall()
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/sessions.html", sessions=[dict(s) for s in my_sessions], unread_count=unread_count)

@app.route("/student/testimonials", methods=["GET", "POST"])
@student_required
def student_testimonials():
    conn = get_db()
    testimonials = conn.execute("SELECT * FROM testimonials").fetchall()
    approved_testimonials = [t for t in testimonials if t["approved"]]
    my_testimonials = [t for t in testimonials if t["student_id"] == session["user"]["id"]]
    
    if request.method == "POST":
        testimonial_text = request.form.get("testimonial", "").strip()
        if testimonial_text:
            student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user"]["id"],)).fetchone()
            max_id = conn.execute("SELECT MAX(id) as max_id FROM testimonials").fetchone()
            new_id = (max_id["max_id"] or 0) + 1
            
            conn.execute('''
                INSERT INTO testimonials (id, student_id, student_name, course, testimonial, date, approved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, session["user"]["id"], student["name"] if student else session["user"]["name"],
                  student["course"] if student else "", testimonial_text, datetime.now().strftime("%Y-%m-%d"), 0))
            conn.commit()
            conn.close()
            flash("Testimonial submitted successfully! It will be visible after admin approval.", "success")
            return redirect(url_for("student_testimonials"))
        else:
            conn.close()
            flash("Please enter your testimonial.", "error")
    
    conn.close()
    unread_count = get_unread_count(session["user"]["id"])
    return render_template("student/testimonials.html", 
                           testimonials=[dict(t) for t in approved_testimonials],
                           my_testimonials=[dict(t) for t in my_testimonials],
                           unread_count=unread_count)

@app.route("/student/end-session/<int:session_id>")
@student_required
def student_end_session(session_id):
    conn = get_db()
    conn.execute('''
        UPDATE sessions SET status = "DONE", time_out = ? WHERE id = ? AND student_id = ?
    ''', (datetime.now().strftime("%H:%M"), session_id, session["user"]["id"]))
    
    conn.execute('''
        UPDATE students SET active_session = 0, current_lab = NULL, current_subject = NULL, 
                          login_time = NULL, reward_points = reward_points + 10
        WHERE id = ?
    ''', (session["user"]["id"],))
    
    conn.commit()
    conn.close()
    
    add_notification(session["user"]["id"], "Your sit-in session has been marked as done. You earned 10 reward points!")
    flash("Session marked as done. You earned 10 reward points!", "success")
    return redirect(url_for("student_history"))

# ─── Admin Routes ────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or session["user"].get("role") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    reservations = conn.execute("SELECT * FROM reservations").fetchall()
    active_sitin = [s for s in sessions_data if s["status"] == "ACTIVE"]
    recent = sorted(sessions_data, key=lambda x: x["id"], reverse=True)[:5]
    pending_reservations = [r for r in reservations if r["status"] == "PENDING"]
    feedback_sessions = [s for s in sessions_data if s["feedback"] and s["feedback"].strip()]
    stats = {
        "total_students": len(students),
        "active_sitins": len(active_sitin),
        "total_sitins": len(sessions_data),
        "reservations": len(reservations),
        "pending_reservations": len(pending_reservations),
        "feedback_count": len(feedback_sessions)
    }
    conn.close()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_sitins=[dict(s) for s in recent],
        pending_reservations=[dict(r) for r in pending_reservations],
        recent_feedback=[dict(s) for s in sorted(feedback_sessions, key=lambda x: x["id"], reverse=True)[:5]]
    )

@app.route("/admin/search-student", methods=["GET", "POST"])
@admin_required
def admin_search_student():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip().lower()
        conn = get_db()
        result = conn.execute('''
            SELECT * FROM students WHERE LOWER(name) LIKE ? OR LOWER(id) LIKE ?
        ''', (f"%{query}%", f"%{query}%")).fetchall()
        conn.close()
        result = [dict(r) for r in result]
    return render_template("admin/search_student.html", result=result, query=query)

@app.route("/admin/student-list")
@admin_required
def admin_student_list():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("admin/student_list.html", students=[dict(s) for s in students])

@app.route("/admin/student/delete/<student_id>", methods=["POST"])
@admin_required
def admin_delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash(f"Student {student_id} has been deleted.", "success")
    return redirect(url_for("admin_student_list"))

@app.route("/admin/student/reset-sessions/<student_id>", methods=["POST"])
@admin_required
def admin_reset_student_sessions(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        flash("Student not found.", "error")
        return redirect(url_for("admin_student_list"))
    
    conn.execute("UPDATE students SET sessions_left = 30 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash(f"Sessions reset to 30 for {student['name']}.", "success")
    return redirect(url_for("admin_student_list"))

@app.route("/admin/student/view/<student_id>")
@admin_required
def admin_view_student(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        flash("Student not found.", "error")
        return redirect(url_for("admin_student_list"))
    student_sessions = conn.execute('''
        SELECT * FROM sessions WHERE student_id = ?
    ''', (student_id,)).fetchall()
    all_students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("admin/student_list.html", students=[dict(s) for s in all_students],
                           view_student=dict(student), student_sessions=[dict(s) for s in student_sessions])

@app.route("/admin/log-sitin", methods=["GET", "POST"])
@admin_required
def admin_log_sitin():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    if request.method == "POST":
        student_id = request.form.get("student_id")
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if student:
            max_id = conn.execute("SELECT MAX(id) as max_id FROM sessions").fetchone()
            new_id = (max_id["max_id"] or 0) + 1
            
            conn.execute('''
                INSERT INTO sessions (id, student_id, student_name, lab, subject, date, time_in, time_out, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, student_id, student["name"], request.form.get("lab"), request.form.get("subject"),
                  datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"), None, "ACTIVE"))
            
            conn.execute('''
                UPDATE students SET active_session = 1, current_lab = ?, current_subject = ?, 
                                      login_time = ?, sit_in_count = sit_in_count + 1,
                                      sessions_left = CASE WHEN sessions_left > 0 THEN sessions_left - 1 ELSE 0 END
                WHERE id = ?
            ''', (request.form.get("lab"), request.form.get("subject"), datetime.now().strftime("%H:%M"), student_id))
            
            conn.commit()
            conn.close()
            flash(f"Sit-in logged for {student['name']}.", "success")
        else:
            conn.close()
            flash("Student not found.", "error")
        return redirect(url_for("admin_log_sitin"))
    conn.close()
    return render_template("admin/log_sitin.html", students=[dict(s) for s in students])

@app.route("/admin/current-sitins")
@admin_required
def admin_current_sitins():
    conn = get_db()
    active = conn.execute('SELECT * FROM sessions WHERE status = "ACTIVE"').fetchall()
    conn.close()
    return render_template("admin/current_sitin.html", sessions=[dict(s) for s in active])

@app.route("/admin/end-sitin/<int:session_id>")
@admin_required
def admin_end_sitin(session_id):
    conn = get_db()
    session_data = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if session_data:
        conn.execute('UPDATE sessions SET status = "DONE", time_out = ? WHERE id = ?', 
                    (datetime.now().strftime("%H:%M"), session_id))
        conn.execute('''
            UPDATE students SET active_session = 0, current_lab = NULL, current_subject = NULL, 
                              login_time = NULL, reward_points = reward_points + 10
            WHERE id = ?
        ''', (session_data["student_id"],))
        conn.commit()
        add_notification(session_data["student_id"], "Your sit-in session has been ended by the admin. You earned 10 reward points!")
        conn.close()
        flash("Sit-in session ended successfully.", "success")
    else:
        conn.close()
        flash("Session not found.", "error")
    return redirect(url_for("admin_current_sitins"))

@app.route("/admin/records")
@admin_required
def admin_records():
    conn = get_db()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    return render_template("admin/records.html", sessions=[dict(s) for s in sessions_data])


@app.route("/admin/records/download")
@admin_required
def admin_records_download():
    from flask import Response
    import csv
    conn = get_db()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Student Name", "Student ID", "Lab", "Subject", "Date", "Time In", "Time Out", "Status"])
    for i, s in enumerate(sessions_data, 1):
        writer.writerow([
            i,
            s["student_name"],
            s["student_id"],
            s["lab"],
            s["subject"],
            s["date"],
            s["time_in"],
            s["time_out"] or "",
            s["status"]
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sitin_records.csv"}
    )

@app.route("/admin/records/pdf")
@admin_required
def admin_records_pdf():
    from flask import Response
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from PIL import Image as PILImage

    conn = get_db()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=8)
    subtitle_style = ParagraphStyle('subtitle', parent=styles['Heading2'], fontSize=12, leading=14, spaceAfter=4)
    normal_style = ParagraphStyle('normal', parent=styles['Normal'], fontSize=10, leading=13)

    elements = []
    logo_path = os.path.join(app.root_path, 'static', 'images', 'uclogo.webp')
    try:
        pil_logo = PILImage.open(logo_path).convert('RGB')
        logo_buffer = io.BytesIO()
        pil_logo.save(logo_buffer, format='PNG')
        logo_buffer.seek(0)
        logo = Image(logo_buffer, width=0.9 * inch, height=0.9 * inch)
        elements.append(logo)
    except Exception:
        pass

    elements.append(Paragraph('University of Cebu', title_style))
    elements.append(Paragraph('CCS Sit-in Monitor — Sit-in Records', subtitle_style))
    elements.append(Paragraph(datetime.now().strftime('Generated: %Y-%m-%d %H:%M'), normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    table_data = [["#", "Student", "Student ID", "Lab", "Subject", "Date", "Time In", "Time Out", "Status"]]
    for i, s in enumerate(sessions_data, 1):
        table_data.append([
            str(i),
            s["student_name"],
            s["student_id"],
            s["lab"],
            s["subject"],
            s["date"],
            s["time_in"],
            s["time_out"] or '—',
            s["status"],
        ])

    col_widths = [0.35 * inch, 1.4 * inch, 0.9 * inch, 0.8 * inch, 1.2 * inch, 0.8 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch]
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph('Generated from CCS Sit-in Monitor system', normal_style))

    doc.build(elements)
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=sitin_records.pdf'}
    )

@app.route("/admin/reservation")
@admin_required
def admin_reservation():
    conn = get_db()
    reservations = conn.execute("SELECT * FROM reservations").fetchall()
    pc_status_rows = conn.execute("SELECT * FROM pc_status").fetchall()
    pc_status = {}
    for row in pc_status_rows:
        if row["lab"] not in pc_status:
            pc_status[row["lab"]] = {}
        pc_status[row["lab"]][row["pc_number"]] = row["status"]
    conn.close()
    labs = ["Lab 1", "Lab 2", "Lab 3"]
    for lab in labs:
        if lab not in pc_status:
            pc_status[lab] = {}
        for i in range(1, 31):
            if str(i) not in pc_status[lab]:
                pc_status[lab][str(i)] = "available"
    return render_template("admin/admin_reservation.html", reservations=[dict(r) for r in reservations], pc_status=pc_status, labs=labs)

@app.route("/admin/reservation/approve/<int:res_id>")
@admin_required
def admin_approve_reservation(res_id):
    conn = get_db()
    reservation = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    if reservation:
        conn.execute('UPDATE reservations SET status = "APPROVED" WHERE id = ?', (res_id,))
        
        max_id = conn.execute("SELECT MAX(id) as max_id FROM sessions").fetchone()
        new_id = (max_id["max_id"] or 0) + 1
        
        conn.execute('''
            INSERT INTO sessions (id, student_id, student_name, lab, subject, date, time_in, time_out, status, pc_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, reservation["student_id"], reservation["student_name"], reservation["lab"],
              reservation["subject"], reservation["date"], datetime.now().strftime("%H:%M"), None, "ACTIVE", reservation["pc_number"]))
        
        conn.execute('''
            UPDATE students SET active_session = 1, current_lab = ?, current_subject = ?, 
                              login_time = ?, sit_in_count = sit_in_count + 1,
                              sessions_left = CASE WHEN sessions_left > 0 THEN sessions_left - 1 ELSE 0 END
            WHERE id = ?
        ''', (reservation["lab"], reservation["subject"], datetime.now().strftime("%H:%M"), reservation["student_id"]))
        
        conn.commit()
        add_notification(reservation["student_id"], f"Your reservation for {reservation['lab']} PC {reservation['pc_number']} has been approved.")
        conn.close()
        flash("Reservation approved successfully.", "success")
    else:
        conn.close()
        flash("Reservation not found.", "error")
    return redirect(url_for("admin_reservation"))


@app.route("/admin/reservation/reject/<int:res_id>")
@admin_required
def admin_reject_reservation(res_id):
    conn = get_db()
    reservation = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    if reservation:
        conn.execute('UPDATE reservations SET status = "REJECTED" WHERE id = ?', (res_id,))
        conn.commit()
        add_notification(reservation["student_id"], f"Your reservation for {reservation['lab']} PC {reservation['pc_number']} has been rejected.")
        conn.close()
        flash("Reservation rejected successfully.", "success")
    else:
        conn.close()
        flash("Reservation not found.", "error")
    return redirect(url_for("admin_reservation"))


@app.route("/admin/reservation/pc-status", methods=["POST"])
@admin_required
def admin_update_pc_status():
    lab = request.form.get("lab")
    pc = request.form.get("pc")
    status = request.form.get("status")
    valid_statuses = ["available", "unavailable", "under_maintenance", "reserved"]
    if lab and pc and status in valid_statuses:
        conn = get_db()
        conn.execute('''
            INSERT OR REPLACE INTO pc_status (lab, pc_number, status)
            VALUES (?, ?, ?)
        ''', (lab, pc, status))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid data"}), 400

@app.route("/admin/reservation/pc-status/bulk", methods=["POST"])
@admin_required
def admin_update_pc_status_bulk():
    lab = request.form.get("lab")
    status = request.form.get("status")
    pcs = request.form.get("pcs", "")
    valid_statuses = ["available", "unavailable", "under_maintenance", "reserved"]

    if not lab or status not in valid_statuses:
        return jsonify({"success": False, "error": "Invalid data"}), 400

    pc_numbers = [pc.strip() for pc in pcs.split(',') if pc.strip()]
    conn = get_db()

    if pc_numbers:
        for pc in pc_numbers:
            conn.execute('''
                INSERT OR REPLACE INTO pc_status (lab, pc_number, status)
                VALUES (?, ?, ?)
            ''', (lab, pc, status))
    else:
        for i in range(1, 31):
            conn.execute('''
                INSERT OR REPLACE INTO pc_status (lab, pc_number, status)
                VALUES (?, ?, ?)
            ''', (lab, str(i), status))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/admin/rewards")
@admin_required
def admin_rewards():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY reward_points DESC").fetchall()
    conn.close()
    return render_template("admin/rewards.html", leaderboard=[dict(s) for s in students])

@app.route("/admin/rewards/give-points", methods=["POST"])
@admin_required
def admin_give_points():
    student_id = request.form.get("student_id", "").strip()
    try:
        points = int(request.form.get("points", 0))
    except ValueError:
        points = 0
    reason = request.form.get("reason", "Manual award").strip() or "Manual award"

    if not student_id or points <= 0:
        flash("Invalid student or points value.", "error")
        return redirect(url_for("admin_rewards"))

    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student:
        conn.execute('UPDATE students SET reward_points = reward_points + ? WHERE id = ?', (points, student_id))
        conn.commit()
        conn.close()
        flash(f"Added {points} points to {student['name']} — {reason}.", "success")
    else:
        conn.close()
        flash("Student not found.", "error")

    return redirect(url_for("admin_rewards"))

@app.route("/admin/announcements", methods=["GET", "POST"])
@admin_required
def admin_announcements():
    conn = get_db()
    announcements = conn.execute("SELECT * FROM announcements ORDER BY date DESC").fetchall()
    if request.method == "POST":
        max_id = conn.execute("SELECT MAX(id) as max_id FROM announcements").fetchone()
        new_id = (max_id["max_id"] or 0) + 1
        
        conn.execute('''
            INSERT INTO announcements (id, title, body, date)
            VALUES (?, ?, ?, ?)
        ''', (new_id, request.form.get("title", "").strip(), request.form.get("body", "").strip(), datetime.now().strftime("%Y-%m-%d")))
        
        students = conn.execute("SELECT id FROM students").fetchall()
        for st in students:
            add_notification(st["id"], f"New Announcement: {request.form.get('title', '').strip()}")
        
        conn.commit()
        conn.close()
        flash("Announcement posted.", "success")
        return redirect(url_for("admin_announcements"))
    conn.close()
    return render_template("admin/announcements.html", announcements=[dict(a) for a in announcements])

@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    return render_template("admin/analytics.html", students=[dict(s) for s in students], sessions=[dict(s) for s in sessions_data])

@app.route("/admin/reports")
@admin_required
def admin_reports():
    conn = get_db()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    return render_template("admin/reports.html", sessions=[dict(s) for s in sessions_data])

@app.route("/admin/reports/pdf")
@admin_required
def admin_reports_pdf():
    conn = get_db()
    sessions_data = conn.execute("SELECT * FROM sessions").fetchall()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("admin/reports_pdf.html",
                           sessions=[dict(s) for s in sessions_data],
                           students=[dict(s) for s in students],
                           generated=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/admin/testimonials", methods=["GET", "POST"])
@admin_required
def admin_testimonials():
    conn = get_db()
    
    # ─── HANDLE FORM POST ACTIONS (Match your HTML forms exactly) ───
    if request.method == "POST":
        testimonial_id = request.form.get("testimonial_id")
        action = request.form.get("action")
        
        if testimonial_id and action:
            if action == "approve":
                conn.execute('UPDATE testimonials SET approved = 1 WHERE id = ?', (testimonial_id,))
                conn.commit()
                flash("Testimonial approved successfully!", "success")
                
            elif action == "reject" or action == "delete":
                # Both reject and delete forms remove the item from the database
                conn.execute('DELETE FROM testimonials WHERE id = ?', (testimonial_id,))
                conn.commit()
                flash("Testimonial removed successfully.", "success")
                
        return redirect(url_for("admin_testimonials"))

    # ─── HANDLE GET DATA DISPLAY (Match your HTML variable loops exactly) ───
    all_testimonials = conn.execute("SELECT * FROM testimonials ORDER BY date DESC").fetchall()
    conn.close()
    
    # Convert rows to dicts and filter them by approval flag status
    pending = [dict(t) for t in all_testimonials if not t["approved"]]
    approved = [dict(t) for t in all_testimonials if t["approved"]]
    
    return render_template(
        "admin/testimonials.html", 
        pending_testimonials=pending, 
        approved_testimonials=approved
    )
    

@app.route("/admin/software-apps", methods=["GET", "POST"])
@admin_required
def admin_software_apps():
    conn = get_db()
    selected_lab = request.args.get("lab", "All Labs")
    software_apps = conn.execute("SELECT * FROM software_apps").fetchall()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            max_id = conn.execute("SELECT MAX(id) as max_id FROM software_apps").fetchone()
            new_id = (max_id["max_id"] or 0) + 1

            conn.execute('''
                INSERT INTO software_apps (id, name, category, version, lab, description, installed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, request.form.get("name", "").strip(), request.form.get("category", "").strip(),
                  request.form.get("version", "").strip(), request.form.get("lab", "").strip(),
                  request.form.get("description", "").strip(), request.form.get("installed") == "on"))
            conn.commit()
            flash(f"Software '{request.form.get('name', '').strip()}' added successfully.", "success")
        elif action == "delete":
            app_id = request.form.get("app_id")
            conn.execute("DELETE FROM software_apps WHERE id = ?", (app_id,))
            conn.commit()
            flash("Software deleted successfully.", "success")
        elif action == "toggle":
            app_id = request.form.get("app_id")
            app = conn.execute("SELECT * FROM software_apps WHERE id = ?", (app_id,)).fetchone()
            if app:
                conn.execute('UPDATE software_apps SET installed = ? WHERE id = ?', (not app["installed"], app_id))
                conn.commit()
            flash("Software status updated.", "success")

        conn.close()
        return redirect(url_for("admin_software_apps", lab=selected_lab) if selected_lab else url_for("admin_software_apps"))

    labs_rows = conn.execute("SELECT DISTINCT lab FROM software_apps WHERE lab IS NOT NULL AND lab != ''").fetchall()
    conn.close()

    existing_labs = sorted({row["lab"] for row in labs_rows if row["lab"]})
    lab_options = ["All Labs", "Lab 1", "Lab 2", "Lab 3"] + [lab for lab in existing_labs if lab not in {"All Labs", "Lab 1", "Lab 2", "Lab 3"}]
    labs = ["All Labs"] + [lab for lab in existing_labs if lab != "All Labs"]
    software_apps = [dict(a) for a in software_apps]
    if selected_lab and selected_lab != "All Labs":
        software_apps = [app for app in software_apps if app["lab"] == selected_lab]

    return render_template(
        "admin/software_apps.html",
        software_apps=software_apps,
        labs=labs,
        lab_options=lab_options,
        selected_lab=selected_lab
    )

@app.route("/admin/software-apps/import", methods=["POST"])
@admin_required
def admin_software_apps_import():
    if 'file' not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("admin_software_apps"))
    
    file = request.files['file']
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for("admin_software_apps"))
    
    if file and file.filename.endswith('.json'):
        try:
            import json
            data = json.load(file)
            conn = get_db()
            
            for app in data:
                max_id = conn.execute("SELECT MAX(id) as max_id FROM software_apps").fetchone()
                new_id = (max_id["max_id"] or 0) + 1
                
                conn.execute('''
                    INSERT INTO software_apps (id, name, category, version, lab, description, installed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (new_id, app.get("name", ""), app.get("category", ""), app.get("version", ""),
                      app.get("lab", ""), app.get("description", ""), app.get("installed", True)))
            
            conn.commit()
            conn.close()
            flash(f"Successfully imported {len(data)} software applications.", "success")
        except Exception as e:
            flash(f"Error importing file: {str(e)}", "error")
    else:
        flash("Please upload a valid JSON file.", "error")
    
    return redirect(url_for("admin_software_apps"))

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)