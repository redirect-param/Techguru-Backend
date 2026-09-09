import os
import sqlite3
import secrets
import math
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, abort

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max upload limit
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage.db')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                share_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

init_db()

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        original_name = file.filename
        file_ext = os.path.splitext(original_name)[1]
        stored_name = f"{secrets.token_hex(16)}{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        mime_type = file.content_type or 'application/octet-stream'
        share_token = secrets.token_urlsafe(12)

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO files (original_name, stored_name, file_size, mime_type, share_token) VALUES (?, ?, ?, ?, ?)',
                (original_name, stored_name, file_size, mime_type, share_token)
            )
            file_id = cursor.lastrowid
            db.commit()

        return jsonify({
            'message': 'File uploaded successfully',
            'file': {
                'id': file_id,
                'name': original_name,
                'size': format_size(file_size),
                'type': mime_type,
                'share_token': share_token
            }
        }), 201

@app.route('/api/files', methods=['GET'])
def get_files():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM files ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        files = []
        total_bytes = 0
        for row in rows:
            total_bytes += row['file_size']
            files.append({
                'id': row['id'],
                'original_name': row['original_name'],
                'file_size': format_size(row['file_size']),
                'raw_size': row['file_size'],
                'mime_type': row['mime_type'],
                'share_token': row['share_token'],
                'created_at': row['created_at']
            })
            
    return jsonify({
        'files': files,
        'total_storage': format_size(total_bytes),
        'file_count': len(files)
    })

@app.route('/api/download/<int:file_id>', methods=['GET'])
def download_file(file_id):
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
        file_record = cursor.fetchone()

    if not file_record:
        return jsonify({'error': 'File not found'}), 404

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        file_record['stored_name'],
        as_attachment=True,
        download_name=file_record['original_name']
    )

@app.route('/s/<share_token>', methods=['GET'])
def share_link(share_token):
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM files WHERE share_token = ?', (share_token,))
        file_record = cursor.fetchone()

    if not file_record:
        abort(404)

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        file_record['stored_name'],
        as_attachment=True,
        download_name=file_record['original_name']
    )

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
        file_record = cursor.fetchone()

        if not file_record:
            return jsonify({'error': 'File not found'}), 404

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record['stored_name'])
        if os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
        db.commit()

    return jsonify({'message': 'File deleted successfully'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)