import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

# Database file path
DB_FOLDER = "data"
DB_NAME = "feedback_system.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

def get_connection():
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except:
        pass
        
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    print("⚡ Initializing Multi-Tenant Intelligence Database...")

    # 1. USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT CHECK(role IN ('superadmin','admin','teacher','student')) NOT NULL,
        status TEXT CHECK(status IN ('pending','approved','rejected')) DEFAULT 'pending',
        college_code TEXT NOT NULL,
        otp_code TEXT DEFAULT NULL,
        otp_expiry DATETIME DEFAULT NULL,
        is_verified BOOLEAN DEFAULT 0,
        created_at TEXT
    )
    """)

    # 2. TEACHERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        full_name TEXT,
        college_code TEXT,
        department TEXT,
        position TEXT,
        class_year TEXT,
        division TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 3. STUDENTS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        full_name TEXT,
        prn_number TEXT UNIQUE,
        college_code TEXT,
        mobile_no TEXT,
        department TEXT,
        class_name TEXT,
        academic_year TEXT,
        teacher_name TEXT,
        hod_name TEXT,
        assigned_teacher_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
    )
    """)

    # 4. FEEDBACK FORMS (Updated with ai_summary column for Qwen results)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback_forms (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        college_code TEXT,
        created_at TEXT,
        teacher_id INTEGER,
        ai_summary TEXT DEFAULT NULL,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    )
    """)

    # 5. FEEDBACK RESPONSES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id TEXT,
        student_id INTEGER,
        college_code TEXT,
        feedback TEXT,
        sentiment TEXT,
        submitted_at TEXT,
        FOREIGN KEY (form_id) REFERENCES feedback_forms(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # 6. APPROVAL LOGS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS approval_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acted_by_user_id INTEGER,
        target_user_id INTEGER,
        college_code TEXT,
        action TEXT,
        role TEXT,
        action_date TEXT
    )
    """)

    # ---------------- INITIALIZE SYSTEM ROLES ----------------

    # A. CREATE MASTER SUPER ADMIN (OM DHAGE)
    try:
        cur.execute("SELECT id FROM users WHERE email='omdhage.dev@gmail.com'")
        if not cur.fetchone():
            hashed_master_password = generate_password_hash("dhage04")
            cur.execute("""
            INSERT INTO users (email, password, role, status, college_code, is_verified, created_at)
            VALUES (?, ?, 'superadmin', 'approved', 'GLOBAL', 1, ?)
            """, (
                "omdhage.dev@gmail.com",
                hashed_master_password,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            print("👑 Super Admin Initialized: omdhage.dev@gmail.com / dhage04")
    except Exception as e:
        print(f"⚠️ Error initializing superadmin: {e}")

    # B. CREATE DEFAULT COLLEGE ADMIN (TEST ACCOUNT)
    try:
        cur.execute("SELECT id FROM users WHERE email='admin@college.com'")
        if not cur.fetchone():
            hashed_admin_password = generate_password_hash("admin123")
            cur.execute("""
            INSERT INTO users (email, password, role, status, college_code, is_verified, created_at)
            VALUES (?, ?, 'admin', 'approved', 'AIFB001', 1, ?)
            """, (
                "admin@college.com",
                hashed_admin_password,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            print("✅ Default College Admin Initialized: admin@college.com / admin123")
    except Exception as e:
        print(f"⚠️ Error initializing admin: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Database Ready at: {DB_PATH}")

if __name__ == "__main__":
    init_db()