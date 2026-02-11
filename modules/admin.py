import streamlit as st
from datetime import datetime
import pandas as pd
from db import get_connection

# ---------------- ADMIN LOGIN ----------------
def admin_login():
    st.subheader("🔐 Admin Login")

    email = st.text_input("Admin Email", key="admin_login_email")
    password = st.text_input("Password", type="password", key="admin_login_password")

    if st.button("Login", key="admin_login_btn"):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, status
            FROM users
            WHERE email=? AND password=? AND role='admin'
        """, (email, password))

        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Invalid admin credentials")
            return

        user_id, status = row

        if status != "approved":
            st.error("Admin account not approved")
            return

        st.session_state.admin_logged_in = True
        st.session_state.admin_user_id = user_id
        st.success("Admin login successful")
        st.rerun()

# ---------------- ADD TEACHER ----------------
def add_teacher():
    st.subheader("➕ Add Teacher")

    name = st.text_input("Full Name", key="add_teacher_name")
    department = st.text_input("Department", key="add_teacher_dept")
    designation = st.text_input("Designation", key="add_teacher_desig")
    email = st.text_input("Email", key="add_teacher_email")
    password = st.text_input("Password", type="password", key="add_teacher_password")

    if st.button("Create Teacher", key="add_teacher_btn"):
        if not all([name, email, password]):
            st.warning("Please fill all required fields")
            return

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (email, password, role, status, created_at)
                VALUES (?, ?, 'teacher', 'approved', ?)
            """, (
                email,
                password,
                datetime.now().strftime("%d %b %Y %H:%M")
            ))

            user_id = cur.lastrowid

            cur.execute("""
                INSERT INTO teachers (user_id, full_name, department, designation)
                VALUES (?, ?, ?, ?)
            """, (user_id, name, department, designation))

            conn.commit()
            st.success("Teacher added and approved")

        except Exception:
            st.error("Teacher already exists")

        finally:
            conn.close()

# ---------------- MANAGE TEACHERS ----------------
def manage_teachers():
    st.subheader("👩‍🏫 Manage Teachers")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT users.id, teachers.full_name, users.email, users.status
        FROM users
        JOIN teachers ON teachers.user_id = users.id
        WHERE users.role='teacher'
    """)

    teachers = cur.fetchall()

    if not teachers:
        st.info("No teachers found")
        conn.close()
        return

    for user_id, name, email, status in teachers:
        with st.expander(f"{name} | {email} | {status.upper()}"):
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Approve", key=f"approve_teacher_{user_id}"):
                    cur.execute("UPDATE users SET status='approved' WHERE id=?", (user_id,))
                    conn.commit()
                    st.success("Teacher approved")
                    st.rerun()

            with col2:
                if st.button("❌ Reject", key=f"reject_teacher_{user_id}"):
                    cur.execute("UPDATE users SET status='rejected' WHERE id=?", (user_id,))
                    conn.commit()
                    st.error("Teacher rejected")
                    st.rerun()

    conn.close()

# ---------------- VIEW STUDENTS ----------------
def view_students():
    st.subheader("🧑‍🎓 All Students")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT students.full_name, students.prn_number, users.status
        FROM students
        JOIN users ON users.id = students.user_id
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        st.info("No students found")
        return

    df = pd.DataFrame(rows, columns=["Name", "PRN", "Status"])
    st.dataframe(df, use_container_width=True)

# ---------------- VIEW ALL FEEDBACKS ----------------
def view_all_feedbacks():
    st.subheader("📊 All Feedbacks (System-wide)")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT feedback_forms.title,
               feedback_responses.feedback,
               feedback_responses.sentiment
        FROM feedback_responses
        JOIN feedback_forms ON feedback_forms.id = feedback_responses.form_id
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        st.info("No feedback available")
        return

    df = pd.DataFrame(rows, columns=["Feedback Title", "Feedback", "Sentiment"])
    st.dataframe(df, use_container_width=True)
    st.bar_chart(df["Sentiment"].value_counts())

# ---------------- VIEW APPROVAL LOGS ----------------
def view_approval_logs():
    st.subheader("📜 Approval Logs")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT acted_by_user_id, target_user_id, action, role, action_date
        FROM approval_logs
        ORDER BY action_date DESC
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        st.info("No approval logs found")
        return

    df = pd.DataFrame(
        rows,
        columns=["By User ID", "Target User ID", "Action", "Role", "Date"]
    )
    st.dataframe(df, use_container_width=True)

# ---------------- ADMIN DASHBOARD ----------------
def admin_dashboard():
    st.header("🛠️ Admin Dashboard")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Add Teacher",
        "Manage Teachers",
        "View Students",
        "View Feedbacks",
        "Approval Logs"
    ])

    with tab1:
        add_teacher()

    with tab2:
        manage_teachers()

    with tab3:
        view_students()

    with tab4:
        view_all_feedbacks()

    with tab5:
        view_approval_logs()

    st.markdown("---")
    if st.button("🚪 Logout", key="admin_logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

# ---------------- MAIN PAGE ----------------
def page():
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        admin_login()
    else:
        admin_dashboard()