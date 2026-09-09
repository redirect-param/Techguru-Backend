import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_NAME = "gitongu_hs.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Students
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            form TEXT NOT NULL,
            stream TEXT NOT NULL,
            fee_balance REAL NOT NULL,
            guardian_contact TEXT NOT NULL
        )
    ''')

    # Staff / Teachers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT NOT NULL,
            image_url TEXT
        )
    ''')

    # Courses / Subjects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')

    # News / Events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')

    # Admissions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT NOT NULL,
            parent_email TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            target_form TEXT NOT NULL,
            kcpe_marks INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Fee Structure
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_level TEXT NOT NULL,
            tuition REAL NOT NULL,
            boarding REAL NOT NULL,
            activity_fee REAL NOT NULL,
            development REAL NOT NULL,
            total REAL NOT NULL
        )
    ''')

    conn.commit()

    # Seed Sample Data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO staff (name, role, department, email, image_url) VALUES (?, ?, ?, ?, ?)
        ''', [
            ("Dr. Samuel Gitongu", "Principal", "Administration", "principal@gitonguhigh.ac.ke", "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&q=80&w=400"),
            ("Mrs. Grace Wanjiku", "Deputy Principal", "Academics", "deputy@gitonguhigh.ac.ke", "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=400"),
            ("Mr. David Ochieng", "Head of Department", "Sciences", "dochieng@gitonguhigh.ac.ke", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=400"),
            ("Ms. Amina Hassan", "Senior Instructor", "Humanities", "ahassan@gitonguhigh.ac.ke", "https://images.unsplash.com/photo-1580894732468-0580859d3a01?auto=format&fit=crop&q=80&w=400")
        ])

    cursor.execute("SELECT COUNT(*) FROM subjects")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO subjects (code, name, department, description) VALUES (?, ?, ?, ?)
        ''', [
            ("MAT101", "Mathematics Core", "Mathematics", "Advanced algebra, calculus, geometry, and problem-solving techniques."),
            ("ENG102", "English Language & Literature", "Languages", "Comprehensive grammar, essay writing, and modern literature studies."),
            ("PHY201", "Physics & Mechanics", "Sciences", "Fundamentals of motion, electricity, thermodynamics, and modern physics."),
            ("BIO202", "Biological Sciences", "Sciences", "Cell biology, ecology, human physiology, and genetics."),
            ("CMP301", "Computer Studies & Coding", "Technical", "Computer fundamentals, basic programming, networking, and digital safety.")
        ])

    cursor.execute("SELECT COUNT(*) FROM fee_structure")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO fee_structure (form_level, tuition, boarding, activity_fee, development, total) VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            ("Form 1", 28000, 18000, 4500, 3500, 54000),
            ("Form 2", 28000, 18000, 4000, 2000, 52000),
            ("Form 3", 30000, 18000, 4000, 2000, 54000),
            ("Form 4", 32000, 18000, 4000, 2000, 56000)
        ])

    cursor.execute("SELECT COUNT(*) FROM news")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO news (title, category, date, content) VALUES (?, ?, ?, ?)
        ''', [
            ("Term 1 2025 Opening Date Announced", "Academic Calendar", "2025-01-10", "All students are expected to report on January 15th, 2025, by 4:00 PM. Clean uniform and cleared fee receipts are mandatory."),
            ("National Science Fair Excellence", "Achievement", "2024-11-28", "Gitongu High School secured 1st position in the National Robotics & Physics Expo held in Nairobi."),
            ("Annual Parent-Teacher Conference", "Event", "2024-12-05", "Join us for the annual review meeting to discuss academic progress, infrastructure updates, and student welfare.")
        ])

    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO students (reg_no, full_name, form, stream, fee_balance, guardian_contact) VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            ("GHS/2023/001", "Kevin Maina", "Form 3", "East", 0.00, "+254712345678"),
            ("GHS/2023/042", "Faith Chebet", "Form 3", "West", 4500.00, "+254722987654"),
            ("GHS/2024/015", "Brian Mwangi", "Form 1", "North", 12000.00, "+254733112233")
        ])

    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news', methods=['GET'])
def get_news():
    conn = get_db_connection()
    news = conn.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in news])

@app.route('/api/staff', methods=['GET'])
def get_staff():
    conn = get_db_connection()
    staff = conn.execute("SELECT * FROM staff").fetchall()
    conn.close()
    return jsonify([dict(row) for row in staff])

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    conn = get_db_connection()
    subjects = conn.execute("SELECT * FROM subjects").fetchall()
    conn.close()
    return jsonify([dict(row) for row in subjects])

@app.route('/api/fees', methods=['GET'])
def get_fees():
    conn = get_db_connection()
    fees = conn.execute("SELECT * FROM fee_structure").fetchall()
    conn.close()
    return jsonify([dict(row) for row in fees])

@app.route('/api/admissions', methods=['POST'])
def apply_admission():
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "Invalid submission"}), 400
    
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO admissions (applicant_name, parent_email, parent_phone, target_form, kcpe_marks)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['applicant_name'], data['parent_email'], data['parent_phone'], data['target_form'], data['kcpe_marks']))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Application submitted successfully! Our admissions team will get back to you."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/student/portal', methods=['POST'])
def student_lookup():
    data = request.json
    reg_no = data.get('reg_no', '').strip()
    
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE UPPER(reg_no) = UPPER(?)", (reg_no,)).fetchone()
    conn.close()
    
    if student:
        return jsonify({"success": True, "student": dict(student)})
    return jsonify({"success": False, "message": "No student record found with this Registration Number."})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)