import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sitin_monitor.db")

def init_database():
    """Initialize SQLite database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            year INTEGER NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            sessions_left INTEGER DEFAULT 30,
            reward_points INTEGER DEFAULT 0,
            sit_in_count INTEGER DEFAULT 0,
            active_session BOOLEAN DEFAULT 0,
            current_lab TEXT,
            current_subject TEXT,
            login_time TEXT,
            avatar TEXT
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            lab TEXT NOT NULL,
            subject TEXT,
            date TEXT NOT NULL,
            time_in TEXT NOT NULL,
            time_out TEXT,
            status TEXT DEFAULT 'ACTIVE',
            pc_number INTEGER,
            feedback TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Reservations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            lab TEXT NOT NULL,
            pc_number INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            subject TEXT,
            status TEXT DEFAULT 'PENDING',
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    # Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            message TEXT NOT NULL,
            date TEXT NOT NULL,
            read BOOLEAN DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Testimonials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS testimonials (
    id INTEGER PRIMARY KEY,
    student_id TEXT,
    student_name TEXT,
    course TEXT,
    testimonial TEXT,
    date TEXT,
    approved INTEGER DEFAULT 0
);
    ''')
    
    # Software Apps table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS software_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            version TEXT,
            lab TEXT NOT NULL,
            description TEXT,
            installed BOOLEAN DEFAULT 1
        )
    ''')
    
    # PC Status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pc_status (
            lab TEXT NOT NULL,
            pc_number TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            PRIMARY KEY (lab, pc_number)
        )
    ''')
    
    # Rewards table (if separate from students)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            points INTEGER NOT NULL,
            reason TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
