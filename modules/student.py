import streamlit as st
from datetime import datetime
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from db import get_connection

# ---------------- LOAD MODEL ----------------
# ---------------- LOAD MODEL ----------------
@st.cache_resource
def load_model():
    # Load the tokenizer from your SAVED folder, not the base one
    # If that fails, fallback to base, but the model MUST be the saved one.
    try:
        model_path = "student_feedback_bert" # Folder created by modeltrain.py
        tokenizer = BertTokenizer.from_pretrained(model_path)
        model = BertForSequenceClassification.from_pretrained(
            model_path,
            num_labels=3
        )
    except OSError:
        st.error("⚠️ Model not found! Please run 'modeltrain.py' first.")
        # Fallback to base just to prevent crash (optional)
        tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=3)
    
    model.eval()
    return tokenizer, model

# ---------------- STUDENT REGISTRATION ----------------
def student_registration():
    st.subheader("📝 Student Registration")

    full_name = st.text_input("Full Name", key="reg_full_name")
    dob = st.date_input("Date of Birth", key="reg_dob")
    prn = st.text_input("PRN Number", key="reg_prn")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_password")

    class_name = st.text_input("Class", key="reg_class")
    guardian_name = st.text_input("Guardian Name", key="reg_guardian")
    guardian_contact = st.text_input("Guardian Contact", key="reg_guardian_contact")
    class_teacher = st.text_input("Class Teacher Name", key="reg_class_teacher")
    hod_name = st.text_input("HOD Name", key="reg_hod")

    if st.button("Register", key="reg_btn"):
        if not all([full_name, prn, email, password]):
            st.warning("Please fill all required fields")
            return

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (email, password, role, status, created_at)
                VALUES (?, ?, 'student', 'pending', ?)
            """, (
                email,
                password,
                datetime.now().strftime("%d %b %Y %H:%M")
            ))

            user_id = cur.lastrowid

            cur.execute("""
                INSERT INTO students (
                    user_id, full_name, date_of_birth, prn_number,
                    class_name, guardian_name, guardian_contact,
                    class_teacher_name, hod_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                full_name,
                dob.strftime("%Y-%m-%d"),
                prn,
                class_name,
                guardian_name,
                guardian_contact,
                class_teacher,
                hod_name
            ))

            conn.commit()
            st.success("Registration successful! Await teacher approval.")

        except Exception:
            st.error("Email or PRN already exists")

        finally:
            conn.close()

# ---------------- STUDENT LOGIN ----------------
def student_login():
    st.subheader("🔐 Student Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_btn"):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT users.status, students.id
            FROM users
            JOIN students ON students.user_id = users.id
            WHERE users.email=? AND users.password=? AND users.role='student'
        """, (email, password))

        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Invalid credentials")
            return

        status, student_id = row

        if status != "approved":
            st.warning(f"Account status: {status.upper()}")
            return

        st.session_state.student_logged_in = True
        st.session_state.student_id = student_id
        st.success("Login successful")
        st.rerun()

# ---------------- STUDENT DASHBOARD ----------------
def student_dashboard():
    st.header("🧑‍🎓 Student Dashboard")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, created_at
        FROM feedback_forms
    """)
    forms = cur.fetchall()

    if not forms:
        st.info("No feedback forms available")
        conn.close()
        return

    titles = [f[1] for f in forms]
    selected = st.selectbox("Select Feedback Topic", titles, key="feedback_select")

    form = next(f for f in forms if f[1] == selected)
    form_id = form[0]

    cur.execute("""
        SELECT 1 FROM feedback_responses
        WHERE form_id=? AND student_id=?
    """, (form_id, st.session_state.student_id))

    if cur.fetchone():
        st.success("You have already submitted feedback for this topic.")
        conn.close()
        return

    feedback = st.text_area("Enter your feedback", key="feedback_text")

    if st.button("Submit Feedback", key="submit_feedback_btn"):
        sentiment = predict_sentiment(feedback)

        cur.execute("""
            INSERT INTO feedback_responses
            (form_id, student_id, feedback, sentiment, submitted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            form_id,
            st.session_state.student_id,
            feedback,
            sentiment,
            datetime.now().strftime("%d %b %Y %H:%M")
        ))

        conn.commit()
        conn.close()

        st.success("Feedback submitted successfully")
        st.info(f"Sentiment detected: **{sentiment}**")

# ---------------- MAIN PAGE ----------------
def page():
    if "student_logged_in" not in st.session_state:
        st.session_state.student_logged_in = False

    tab1, tab2 = st.tabs(["Login", "Register"])

    if not st.session_state.student_logged_in:
        with tab1:
            student_login()
        with tab2:
            student_registration()
    else:
        student_dashboard()