import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sitin_monitor.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def migrate_data():
    """Migrate existing JSON data to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Migrate Students
    print("Migrating students...")
    students = load_json("students.json")
    for student in students:
        cursor.execute('''
            INSERT OR REPLACE INTO students 
            (id, name, course, year, email, password, sessions_left, reward_points, 
             sit_in_count, active_session, current_lab, current_subject, login_time, avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            student.get("id"),
            student.get("name"),
            student.get("course"),
            student.get("year"),
            student.get("email"),
            student.get("password"),
            student.get("sessions_left", 30),
            student.get("reward_points", 0),
            student.get("sit_in_count", 0),
            student.get("active_session", False),
            student.get("current_lab"),
            student.get("current_subject"),
            student.get("login_time"),
            student.get("avatar")
        ))
    print(f"Migrated {len(students)} students")
    
    # Migrate Sessions
    print("Migrating sessions...")
    sessions = load_json("sessions.json")
    for session in sessions:
        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (id, student_id, student_name, lab, subject, date, time_in, time_out, status, pc_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get("id"),
            session.get("student_id"),
            session.get("student_name"),
            session.get("lab"),
            session.get("subject"),
            session.get("date"),
            session.get("time_in"),
            session.get("time_out"),
            session.get("status", "ACTIVE"),
            session.get("pc_number")
        ))
    print(f"Migrated {len(sessions)} sessions")
    
    # Migrate Reservations
    print("Migrating reservations...")
    reservations = load_json("reservations.json")
    for res in reservations:
        cursor.execute('''
            INSERT OR REPLACE INTO reservations 
            (id, student_id, student_name, lab, pc_number, date, time_slot, subject, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            res.get("id"),
            res.get("student_id"),
            res.get("student_name"),
            res.get("lab"),
            res.get("pc_number"),
            res.get("date"),
            res.get("time_slot"),
            res.get("subject"),
            res.get("status", "PENDING")
        ))
    print(f"Migrated {len(reservations)} reservations")
    
    # Migrate Announcements
    print("Migrating announcements...")
    announcements = load_json("announcements.json")
    for ann in announcements:
        cursor.execute('''
            INSERT OR REPLACE INTO announcements 
            (id, title, body, date)
            VALUES (?, ?, ?, ?)
        ''', (
            ann.get("id"),
            ann.get("title"),
            ann.get("body"),
            ann.get("date")
        ))
    print(f"Migrated {len(announcements)} announcements")
    
    # Migrate Notifications
    print("Migrating notifications...")
    notifications = load_json("notifications.json")
    for notif in notifications:
        cursor.execute('''
            INSERT OR REPLACE INTO notifications 
            (id, student_id, message, date, read)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            notif.get("id"),
            notif.get("student_id"),
            notif.get("message"),
            notif.get("date"),
            notif.get("read", False)
        ))
    print(f"Migrated {len(notifications)} notifications")
    
    # Migrate Testimonials
    print("Migrating testimonials...")
    testimonials = load_json("testimonials.json")
    for test in testimonials:
        cursor.execute('''
            INSERT OR REPLACE INTO testimonials 
            (id, student_id, student_name, course, testimonial, date, approved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            test.get("id"),
            test.get("student_id"),
            test.get("student_name"),
            test.get("course"),
            test.get("testimonial"),
            test.get("date"),
            test.get("approved", True)
        ))
    print(f"Migrated {len(testimonials)} testimonials")
    
    # Migrate Software Apps
    print("Migrating software apps...")
    software_apps = load_json("software_apps.json")
    for app in software_apps:
        cursor.execute('''
            INSERT OR REPLACE INTO software_apps 
            (id, name, category, version, lab, description, installed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            app.get("id"),
            app.get("name"),
            app.get("category"),
            app.get("version"),
            app.get("lab"),
            app.get("description"),
            app.get("installed", True)
        ))
    print(f"Migrated {len(software_apps)} software apps")
    
    # Migrate PC Status
    print("Migrating PC status...")
    pc_status = load_json("pc_status.json")
    for lab, pcs in pc_status.items():
        for pc_num, status in pcs.items():
            cursor.execute('''
                INSERT OR REPLACE INTO pc_status 
                (lab, pc_number, status)
                VALUES (?, ?, ?)
            ''', (lab, pc_num, status))
    print(f"Migrated PC status for {len(pc_status)} labs")
    
    # Skip rewards.json - it's leaderboard data, not individual reward transactions
    # Reward points are already stored in the students table
    print("Skipping rewards.json (leaderboard data - points stored in students table)")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_data()
