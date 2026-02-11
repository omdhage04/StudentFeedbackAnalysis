import streamlit as st
from datetime import datetime
import uuid
import pandas as pd
from db import get_connection

# ---------------- TEACHER LOGIN ----------------
def teacher_login():
    st.subheader("🔐 Teacher Login")

    email = st.text_input("Email", key="teacher_login_email")
    password = st.text_input("Password", type="password", key="teacher_login_password")

    if st.button("Login", key="teacher_login_btn"):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT users.id, users.status, teachers.id
            FROM users
            JOIN teachers ON teachers.user_id = users.id
            WHERE users.email=? AND users.password=? AND users.role='teacher'
        """, (email, password))

        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Invalid credentials")
            return

        user_id, status, teacher_id = row

        if status != "approved":
            st.warning(f"Account status: {status.upper()}")
            return

        st.session_state.teacher_logged_in = True
        st.session_state.teacher_user_id = user_id
        st.session_state.teacher_id = teacher_id
        st.success("Login successful")
        st.rerun()

# ---------------- STUDENT APPROVAL ----------------
def student_approval_panel():
    st.subheader("🧑‍🎓 Pending Student Approvals")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT users.id, students.full_name, students.prn_number
        FROM users
        JOIN students ON students.user_id = users.id
        WHERE users.status='pending' AND users.role='student'
    """)

    students = cur.fetchall()

    if not students:
        st.info("No pending students")
        conn.close()
        return

    for user_id, name, prn in students:
        with st.expander(f"{name} | PRN: {prn}"):
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Approve", key=f"approve_{prn}"):
                    cur.execute("UPDATE users SET status='approved' WHERE id=?", (user_id,))
                    cur.execute("""
                        INSERT INTO approval_logs
                        (acted_by_user_id, target_user_id, action, role, action_date)
                        VALUES (?, ?, 'approved', 'student', ?)
                    """, (
                        st.session_state.teacher_user_id,
                        user_id,
                        datetime.now().strftime("%d %b %Y %H:%M")
                    ))
                    conn.commit()
                    st.success("Student approved")
                    st.rerun()

            with col2:
                if st.button("❌ Reject", key=f"reject_{prn}"):
                    cur.execute("UPDATE users SET status='rejected' WHERE id=?", (user_id,))
                    cur.execute("""
                        INSERT INTO approval_logs
                        (acted_by_user_id, target_user_id, action, role, action_date)
                        VALUES (?, ?, 'rejected', 'student', ?)
                    """, (
                        st.session_state.teacher_user_id,
                        user_id,
                        datetime.now().strftime("%d %b %Y %H:%M")
                    ))
                    conn.commit()
                    st.error("Student rejected")
                    st.rerun()

    conn.close()

# ---------------- CREATE FEEDBACK FORM ----------------
def create_feedback_form():
    st.subheader("➕ Create Feedback Form")

    title = st.text_input("Feedback Title", key="teacher_feedback_title")

    if st.button("Create Feedback", key="create_feedback_btn"):
        if not title.strip():
            st.warning("Title cannot be empty")
            return

        conn = get_connection()
        cur = conn.cursor()

        form_id = str(uuid.uuid4())[:8]

        cur.execute("""
            INSERT INTO feedback_forms (id, title, created_at, teacher_id)
            VALUES (?, ?, ?, ?)
        """, (
            form_id,
            title,
            datetime.now().strftime("%d %b %Y"),
            st.session_state.teacher_id
        ))

        conn.commit()
        conn.close()

        st.success("Feedback form created successfully")

# ---------------- VIEW FEEDBACK + ANALYTICS ----------------
def view_feedback_analytics():
    st.subheader("📊 Feedback Analytics")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, created_at
        FROM feedback_forms
        WHERE teacher_id=?
    """, (st.session_state.teacher_id,))

    forms = cur.fetchall()

    if not forms:
        st.info("No feedback forms created yet")
        conn.close()
        return

    for form_id, title, date in forms:
        with st.expander(f"{title} | {date}"):
            cur.execute("""
                SELECT feedback, sentiment
                FROM feedback_responses
                WHERE form_id=?
            """, (form_id,))

            rows = cur.fetchall()

            if not rows:
                st.info("No feedback submitted yet")
                continue

            df = pd.DataFrame(rows, columns=["Feedback", "Sentiment"])
            st.dataframe(df, use_container_width=True)

            st.bar_chart(df["Sentiment"].value_counts())

    conn.close()

# ---------------- DASHBOARD ----------------
def teacher_dashboard():
    st.header("👩‍🏫 Teacher Dashboard")

    tab1, tab2, tab3 = st.tabs([
        "Approve Students",
        "Create Feedback",
        "View Analytics"
    ])

    with tab1:
        student_approval_panel()

    with tab2:
        create_feedback_form()

    with tab3:
        view_feedback_analytics()

    st.markdown("---")
    if st.button("🚪 Logout", key="teacher_logout"):
        st.session_state.teacher_logged_in = False
        st.rerun()

# ---------------- MAIN PAGE ----------------
def page():
    if "teacher_logged_in" not in st.session_state:
        st.session_state.teacher_logged_in = False

    if not st.session_state.teacher_logged_in:
        teacher_login()
    else:
        teacher_dashboard()