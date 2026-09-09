import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
DATABASE = 'portfolio.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                technologies TEXT NOT NULL,
                link TEXT NOT NULL,
                icon TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                proficiency INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experience (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                duration TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Seed Projects if empty
        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            projects_data = [
                ("Enterprise Payment Gateway", "High-throughput payment orchestration engine handling 1M+ daily transactions with 99.99% uptime.", "Fintech", "Python, Flask, PostgreSQL, Redis, Docker", "#", "fa-credit-card"),
                ("Banking Microservices Suite", "Decentralized core banking integration platform providing REST & GraphQL APIs for core ledger ops.", "Enterprise", "Python, Django, AWS ECS, Terraform, Kafka", "#", "fa-building-columns"),
                ("Cloud Cost Optimization Engine", "Automated cloud resource monitoring and optimization pipeline saving 35% monthly infrastructure bill.", "Cloud", "Python, AWS Lambda, Boto3, React, SQLite", "#", "fa-cloud"),
                ("Real-time Telemetry Dashboard", "Scalable data ingestion pipeline streaming IoT metrics with real-time alerting.", "Enterprise", "Python, WebSockets, JavaScript, Redis, Docker", "#", "fa-chart-line")
            ]
            cursor.executemany(
                "INSERT INTO projects (title, description, category, technologies, link, icon) VALUES (?, ?, ?, ?, ?, ?)",
                projects_data
            )

        # Seed Skills if empty
        cursor.execute("SELECT COUNT(*) FROM skills")
        if cursor.fetchone()[0] == 0:
            skills_data = [
                ("Python / Flask / Django", "Backend", 95),
                (" REST & GraphQL APIs", "Backend", 90),
                ("PostgreSQL & SQLite", "Database", 90),
                ("AWS Infrastructure", "Cloud & DevOps", 85),
                ("Docker & Kubernetes", "Cloud & DevOps", 85),
                ("CI/CD & Automation", "Cloud & DevOps", 88),
                ("JavaScript / ES6+", "Frontend", 80),
                ("System Architecture", "Architecture", 92)
            ]
            cursor.executemany(
                "INSERT INTO skills (name, category, proficiency) VALUES (?, ?, ?)",
                skills_data
            )

        # Seed Experience if empty
        cursor.execute("SELECT COUNT(*) FROM experience")
        if cursor.fetchone()[0] == 0:
            exp_data = [
                ("Safaricom PLC", "Lead Backend Architect", "2021 - Present", "Engineered microservices scaling up to millions of active users. Led cross-functional engineering teams in delivering secure payment integrations and cloud modernization."),
                ("Equity Group Holdings", "Senior Software Engineer", "2018 - 2021", "Developed scalable middleware for digital channels. Reduced transaction latency by 40% through query optimization and distributed caching strategies."),
                ("TechAfrica Innovations", "Software Engineer", "2016 - 2018", "Built custom enterprise resource planning (ERP) solutions, RESTful web services, and automated data processing tools for enterprise clients.")
            ]
            cursor.executemany(
                "INSERT INTO experience (company, role, duration, description) VALUES (?, ?, ?, ?)",
                exp_data
            )

        db.commit()

# Route: Main Page
@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM skills")
    skills = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM experience ORDER BY id ASC")
    experience = [dict(row) for row in cursor.fetchall()]

    return render_template('index.html', skills=skills, experience=experience)

# API Route: Get Projects
@app.route('/api/projects', methods=['GET'])
def get_projects():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM projects")
    projects = [dict(row) for row in cursor.fetchall()]
    return jsonify({"status": "success", "data": projects})

# API Route: Contact Form
@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json() if request.is_json else request.form
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()
    
    if not name or not email or not message:
        return jsonify({"status": "error", "message": "Please fill out all required fields."}), 400
        
    db = get_db()
    cursor = db.cursor()
    created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute(
        "INSERT INTO messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, email, subject, message, created_at)
    )
    db.commit()
    
    return jsonify({
        "status": "success",
        "message": "Thank you for reaching out, Julius Mwangi will get back to you shortly."
    }), 201

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)