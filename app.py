from flask import Flask, render_template, request, redirect, jsonify, session, flash, url_for
from flask_cors import CORS
import mysql.connector
import smtplib
from email.message import EmailMessage
import google.generativeai as genai
from dotenv import load_dotenv
import os


load_dotenv()


app = Flask(__name__)
CORS(app)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
app.secret_key = os.getenv("your_secret_key","default_fallback_secret")

username = os.getenv('USERNAME1')
password = os.getenv('PASSWORD')

# MySQL connection config
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )

# Home
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    input_username = request.form['username']
    input_password = request.form['password']

    if input_username == username and input_password == password:
        session['admin_logged_in'] = True
        flash("✅ Login successful", "success")
        return redirect('/login')
    else:
        flash("❌ Invalid username or password", "danger")
        return redirect('/')
    

@app.route('/logout')
def logout():
    session.clear()
    flash("👋 Logged out successfully.", "info")
    return redirect(url_for('login'))
# Home
@app.route('/login')
def index():
    return render_template('index.html')

# Add Class
@app.route('/add-class', methods=['GET', 'POST'])
def add_class():
    if request.method == 'POST':
        class_name = request.form['class_name']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO classes (class_name) VALUES (%s)", (class_name,))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('add_class.html')

# Add Subject
@app.route('/add-subject', methods=['GET', 'POST'])
def add_subject():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        class_id = request.form['class_id']
        subject_name = request.form['subject_name']
        cur.execute("INSERT INTO subjects (class_id, subject_name) VALUES (%s, %s)", (class_id, subject_name))
        conn.commit()
        return redirect('/view-subjects')

    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()
    return render_template('add_subject.html', classes=classes)

# Add Topic
@app.route('/add-topic', methods=['GET', 'POST'])
def add_topic():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        subject_id = request.form['subject_id']
        topic_name = request.form['topic_name']
        cur.execute("INSERT INTO topics (subject_id, topic_name) VALUES (%s, %s)", (subject_id, topic_name))
        conn.commit()
        return redirect('/view-topics')

    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()
    return render_template('add_topic.html', classes=classes)

# Add Question
@app.route('/add-question', methods=['GET', 'POST'])
def add_question():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        topic_id = request.form['topic_id']
        demo_question_text = request.form['question_text']
        prompt_question_text = f"Write the following question in HTML + LaTeX(without $) without document and body part.\n{demo_question_text}"
        text_response = model.generate_content(prompt_question_text)
        question_text = text_response.text
        cur.execute("INSERT INTO questions (topic_id, question_text) VALUES (%s, %s)",
                    (topic_id, question_text))
        conn.commit()
        return redirect('/view-questions')

    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()
    return render_template('add_question.html', classes=classes)

# Dynamic Dropdowns
@app.route('/get-subjects/<int:class_id>')
def get_subjects(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT subject_id, subject_name FROM subjects WHERE class_id = %s", (class_id,))
    subjects = cur.fetchall()
    return jsonify(subjects)

@app.route('/get-topics/<int:subject_id>')
def get_topics(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT topic_id, topic_name FROM topics WHERE subject_id = %s", (subject_id,))
    topics = cur.fetchall()
    return jsonify(topics)

# View Pages
@app.route('/view-classes')
def view_classes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()
    conn.close()
    return render_template('view_classes.html', classes=classes)

@app.route('/view-subjects', methods=['GET', 'POST'])
def view_subjects():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()

    subjects = []
    selected_class_id = None

    if request.method == 'POST':
        selected_class_id = request.form.get('class_id')

        # ✅ JOIN with classes to get class name
        cur.execute("""
            SELECT s.subject_id, s.subject_name, c.class_name
            FROM subjects s
            JOIN classes c ON s.class_id = c.class_id
            WHERE s.class_id = %s
        """, (selected_class_id,))
        subjects = cur.fetchall()

    conn.close()
    return render_template(
        'view_subjects.html',
        classes=classes,
        subjects=subjects,
        selected_class_id=selected_class_id
    )

@app.route('/view-topics', methods=['GET', 'POST'])
def view_topics():
    conn = get_connection()
    cur = conn.cursor()

    # Get all classes
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()

    subjects = []
    topics = []

    selected_class_id = None
    selected_subject_id = None

    if request.method == 'POST':
        selected_class_id = request.form['class_id']
        selected_subject_id = request.form['subject_id']

        # Get subjects of selected class
        cur.execute("SELECT subject_id, subject_name FROM subjects WHERE class_id = %s", (selected_class_id,))
        subjects = cur.fetchall()

        # Get topics under selected subject
        cur.execute("""
            SELECT topics.topic_id, topics.topic_name, subjects.subject_name, classes.class_name
            FROM topics
            JOIN subjects ON topics.subject_id = subjects.subject_id
            JOIN classes ON subjects.class_id = classes.class_id
            WHERE subjects.subject_id = %s
        """, (selected_subject_id,))
        topics = cur.fetchall()
    elif request.method == 'GET':
        # If class is selected via GET (optional AJAX or fallback)
        selected_class_id = request.args.get('class_id')
        if selected_class_id:
            cur.execute("SELECT subject_id, subject_name FROM subjects WHERE class_id = %s", (selected_class_id,))
            subjects = cur.fetchall()

    return render_template(
        'view_topics.html',
        classes=classes,
        subjects=subjects,
        topics=topics,
        selected_class_id=selected_class_id,
        selected_subject_id=selected_subject_id
    )

@app.route('/view-questions', methods=['GET', 'POST'])
def view_questions():
    conn = get_connection()
    cur = conn.cursor()

    # Get all classes for dropdown
    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()

    subjects = []
    topics = []
    questions = []

    selected_class_id = None
    selected_subject_id = None
    selected_topic_id = None

    if request.method == 'POST':
        selected_class_id = request.form.get('class_id')
        selected_subject_id = request.form.get('subject_id')
        selected_topic_id = request.form.get('topic_id')

        # Fetch subjects for the selected class
        if selected_class_id:
            cur.execute("SELECT subject_id, subject_name FROM subjects WHERE class_id = %s", (selected_class_id,))
            subjects = cur.fetchall()

        # Fetch topics for the selected subject
        if selected_subject_id:
            cur.execute("SELECT topic_id, topic_name FROM topics WHERE subject_id = %s", (selected_subject_id,))
            topics = cur.fetchall()

        # Fetch questions for the selected topic
        if selected_topic_id:
            cur.execute("""
                SELECT q.question_id, q.question_text, t.topic_name, s.subject_name, c.class_name
                FROM questions q
                JOIN topics t ON q.topic_id = t.topic_id
                JOIN subjects s ON t.subject_id = s.subject_id
                JOIN classes c ON s.class_id = c.class_id
                WHERE t.topic_id = %s
            """, (selected_topic_id,))
            questions = cur.fetchall()

    conn.close()
    return render_template(
        'view_questions.html',
        classes=classes,
        subjects=subjects,
        topics=topics,
        questions=questions,
        selected_class_id=selected_class_id,
        selected_subject_id=selected_subject_id,
        selected_topic_id=selected_topic_id
    )

@app.route('/update-question/<int:question_id>', methods=['POST'])
def update_question(question_id):
    data = request.get_json()
    new_question = data.get('question_text', '')

    if not new_question:
        return jsonify({'success': False, 'error': 'Empty question'})

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE questions SET question_text = %s WHERE question_id = %s", (new_question, question_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/get-questions/<int:topic_id>')
def get_questions(topic_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT question_id, question_text FROM questions WHERE topic_id = %s", (topic_id,))
    questions = cur.fetchall()
    return jsonify(questions)

# Delete Routes
@app.route('/delete-class/<int:class_id>')
def delete_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM classes WHERE class_id = %s", (class_id,))
    conn.commit()
    return redirect('/view-classes')

@app.route('/delete-subject/<int:subject_id>')
def delete_subject(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
    conn.commit()
    return redirect('/view-subjects')

@app.route('/delete-topic/<int:topic_id>')
def delete_topic(topic_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM topics WHERE topic_id = %s", (topic_id,))
    conn.commit()
    return redirect('/view-topics')

@app.route('/delete-question/<int:question_id>')
def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE question_id = %s", (question_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/view-questions')

# Student Login
@app.route('/student-login', methods=['POST'])
def student_login():
    username = request.form['username']
    password = request.form['password']
    conn = get_connection()
    cur = conn.cursor()
    # Replace 'student_id' with actual column name from DESCRIBE students;
    cur.execute("SELECT id, name FROM students WHERE username = %s AND password = %s", (username, password))
    student = cur.fetchone()

    if student:
        session['user_logged_in'] = True
        session['user_role'] = 'student'
        session['student_name'] = student[1]
        return redirect('/student-dashboard')
    else:
        flash("Invalid student credentials", "danger")
        return redirect('/')

# Student Registration
@app.route('/student-register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO students (name, email, mobile, username, password) VALUES (%s, %s, %s, %s, %s)",
                        (name, email, mobile, username, password))
            conn.commit()
            flash("✅ Registration successful. Please login.", "success")
            return redirect('/')
        except mysql.connector.Error as e:
            flash("❌ Username already exists or database error.", "danger")
            return redirect('/student-register')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, mobile, username, password, created_at FROM students")
        students = cursor.fetchall()
        # Fetch count
        cursor.execute("SELECT COUNT(*) AS total FROM students")
        total_count = cursor.fetchone()['total']
        cursor.close()
        conn.close()
        return render_template('dashboard.html', students=students, total=total_count)
    except Exception as e:
        return f"<h3>Database error: {e}</h3>"

# 📌 Forgot Password Route
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    user_email = request.form["email"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM students WHERE email = %s", (user_email,))
    result = cursor.fetchone()
    conn.close()

    if result:
        username, password = result

        # 📧 Email setup
        msg = EmailMessage()
        msg["Subject"] = "Your \alpha Experts AI Questions Portal Credentials"
        msg["From"] = os.getenv("EMAIL_ID")
        msg["To"] = user_email
        msg.set_content(f"Hello,\n\nYour credentials are:\nUsername: {username}\nPassword: {password}")

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(os.getenv("EMAIL_ID"), os.getenv("EMAIL_ID"))
                smtp.send_message(msg)
            return "✅ Email sent successfully!"
        except Exception as e:
            return f"❌ Email failed: {e}"
    else:
        return "❌ Email not found in our records."


@app.route('/student-dashboard')
def student_dashboard():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT class_id, class_name FROM classes")
    classes = cur.fetchall()
    return render_template('student_classes.html', classes=classes)

@app.route('/subjects/<int:class_id>')
def student_subjects(class_id):
    # Store the selected class_id
    selected_class_id = class_id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT subject_id, subject_name FROM subjects WHERE class_id = %s", (class_id,))
    subjects = cur.fetchall()
    return render_template('student_subjects.html', subjects=subjects, selected_class_id=selected_class_id)

@app.route('/topics/<int:subject_id>')
def student_topics(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT topic_id, topic_name FROM topics WHERE subject_id = %s", (subject_id,))
    topics = cur.fetchall()
    return render_template('student_topics.html', subject_id=subject_id, topics=topics)


PROMPTS = {
    "Solution Generate": "Write in html+latex without document and <body>",
    "Draw Diagram": "Draw Diagram in html with no <body> and no <style>",
    "Draw Tables": "Create table in html with no <body> and no <style>",
}

@app.route('/questions/<int:topic_id>')
def student_questions(topic_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT question_id, question_text FROM questions WHERE topic_id = %s", (topic_id,))
    questions = cur.fetchall()
    return render_template('student_questions.html', topic_id=topic_id, questions=questions, prompts=PROMPTS)


# Route to get AI-generated answer
@app.route('/solve', methods=['POST'])
def solve():
    question = request.json.get('question', '')
    prompt_question = f"Write in Latex without document.{question}"
    prompt_response = model.generate_content(prompt_question)
    text_question = prompt_response.text
    try:
        response = model.generate_content(text_question)
        plain_solution = response.text
        styled_prompt = f"Write Question+Solution with all steps in html+latex.\n{text_question}\n{plain_solution}"
        response = model.generate_content(styled_prompt)
        styled_solution = response.text
    except Exception as e:
        styled_solution = f"<p style='color:red;'>❌ Error: {str(e)}</p>"

    return jsonify({'solution': styled_solution})



@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    selected_key = data.get('selected_key')
    history = data.get('history', [])

    if selected_key not in PROMPTS:
        return jsonify({'reply': f"❌ Invalid prompt: {selected_key}"}), 400

    formatted_messages = []
    for h in history:
        role = 'user' if h['role'] == 'user' else 'model'
        formatted_messages.append({
            "role": role,
            "parts": [h["content"]]
        })

    try:
        response = model.generate_content(formatted_messages)
        prompt_msg = f"{PROMPTS[selected_key]}.{response.text}"
        reply = model.generate_content(prompt_msg)
        return jsonify({'reply': reply.text})
    except Exception as e:
        return jsonify({'reply': f"❌ Error: {str(e)}"})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

