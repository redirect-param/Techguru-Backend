import eventlet
eventlet.monkey_patch()

import os
import re
import sys
import time
import json
import socket
import subprocess
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(
    __name__,
    template_folder=FRONTEND_DIR,
    static_folder=os.path.join(FRONTEND_DIR, 'static'),
    static_url_path='/static'
)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'techguru-secret-key')
CORS(app, resources={r"/api/*": {"origins": "*"}})

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25
)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))
os.makedirs(WORKSPACE_ROOT, exist_ok=True)
RUNNING_APPS = {}  # {proj_id: {url, process, port}}

TEMPLATES = [
    {"id": "ecommerce", "name": "E-commerce Store", "desc": "Flask + SQLite + Cart + Auth + Stripe"},
    {"id": "dashboard", "name": "Admin Dashboard", "desc": "Charts, Tables, Dark UI, Auth"},
    {"id": "blog", "name": "Blog CMS", "desc": "Posts, Comments, Markdown, Tags"},
    {"id": "inventory", "name": "Inventory App", "desc": "Dynamic tables, CRUD, Export CSV"},
    {"id": "portfolio", "name": "Portfolio Site", "desc": "Responsive, Animations, Contact Form"}
]

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def get_gemini_response(prompt, system_instruction="", timeout=300, api_key=None):
    api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise Exception("GEMINI_API_KEY not set. Add it in Secrets panel or .env")
    model = "gemini-3.7-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nTask: {prompt}"}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
    }
    headers = {"Content-Type": "application/json"}
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            data = res.json()
            if res.status_code == 200 and "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            err_msg = data.get("error", {}).get("message", f"HTTP {res.status_code}")
            raise Exception(f"API Error ({model}): {err_msg}")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries:
                socketio.sleep(2)
                continue
            raise Exception(f"Connection/Timeout Error: {str(e)}") from e
        except Exception as e:
            raise e

# --- FRONTEND ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/building')
def building():
    return render_template('building.html')

@app.route('/workspace-view')
def workspace_view():
    return render_template('workspace.html')

# Dynamic Reverse Proxy route for generated dynamic apps
@app.route('/preview/<proj_id>/', defaults={'path': ''})
@app.route('/preview/<proj_id>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_preview(proj_id, path):
    app_info = RUNNING_APPS.get(proj_id)
    if not app_info:
        return "Preview App not running", 404
    target_url = f"http://127.0.0.1:{app_info['port']}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_headers]
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return f"Proxy Error: {str(e)}", 502

# --- API ROUTES ---
@app.route('/api/clarify', methods=['POST'])
def clarify():
    data = request.get_json() or {}
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    questions = [
        {
            "question": "What primary features should be prioritized?",
            "options": ["Core Functionality", "User Authentication", "Custom Styling"]
        },
        {
            "question": "Which backend setup do you prefer?",
            "options": ["Flask + SQLite", "Pure Static Frontend"]
        }
    ]
    return jsonify({'questions': questions})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "workspace": WORKSPACE_ROOT})

@app.route('/api/templates', methods=['GET'])
def list_templates():
    return jsonify(TEMPLATES)

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = []
    if os.path.exists(WORKSPACE_ROOT):
        for name in os.listdir(WORKSPACE_ROOT):
            path = os.path.join(WORKSPACE_ROOT, name)
            if os.path.isdir(path):
                app_info = RUNNING_APPS.get(name, {})
                projects.append({
                    "id": name,
                    "mtime": os.path.getmtime(path),
                    "url": app_info.get("url", f"/preview/{name}/"),
                    "running": name in RUNNING_APPS
                })
    return jsonify(projects)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get('message', '')
    project_id = data.get('project_id')
    api_keys = data.get('api_keys', {})
    if not message:
        return jsonify({"error": "No message"}), 400
    if project_id:
        return handle_project_edit(project_id, message, api_keys)
    return jsonify({"reply": f"Got it. Starting setup for: {message}", "action": "start_build", "prompt": message})

def handle_project_edit(project_id, message, api_keys):
    proj_dir = os.path.join(WORKSPACE_ROOT, project_id)
    if not os.path.exists(proj_dir):
        return jsonify({"error": "Project not found"}), 404
    files = []
    for root, _, filenames in os.walk(proj_dir):
        for fname in filenames:
            rel = os.path.relpath(os.path.join(root, fname), proj_dir)
            files.append(rel)
    sys_prompt = f"You are editing a Flask project in {proj_dir}. Current files: {files}\nReturn ONLY code blocks with file paths. Example: ```app.py\ncode```"
    try:
        raw = get_gemini_response(message, sys_prompt, api_key=api_keys.get('gemini'))
        pattern = r"```([^\n]+)\n(.*?)```"
        matches = re.findall(pattern, raw, re.DOTALL)
        updated = []
        for raw_label, content in matches:
            fname = raw_label.strip().split()[-1]
            path = os.path.normpath(os.path.join(proj_dir, fname))
            if path.startswith(proj_dir):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                updated.append(fname)
        if project_id in RUNNING_APPS:
            restart_app(project_id)
        return jsonify({"reply": f"Updated files: {', '.join(updated)}. Reloading preview.", "updated_files": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('start_build')
def handle_start_build(data):
    idea = data.get('prompt', '')
    answers = data.get('answers', '')
    api_keys = data.get('api_keys', {})

    def send_log(msg, status="info", redirect=False, project_id="", public_url=""):
        emit('build_log', {
            'message': msg,
            'status': status,
            'redirect': redirect,
            'project_id': project_id,
            'public_url': public_url
        })
        socketio.sleep(0)  # Yield execution frame to flush socket events

    proj_id = f"proj-{int(time.time())}"
    proj_dir = os.path.join(WORKSPACE_ROOT, proj_id)
    os.makedirs(proj_dir, exist_ok=True)
    send_log(f"Created project directory: workspace/{proj_id}")

    port = find_free_port()
    combined_prompt = f"Concept: {idea}\nDetails: {answers}\nTarget Port: {port}\nGenerate a complete Flask app. app.py MUST use app.run(host='127.0.0.1', port={port})"
    sys_prompt = "Generate a complete full-stack web application. Python Flask, HTML, CSS, JS.\nCRITICAL: Label EVERY code block with the file path: ```app.py"

    try:
        raw_response = get_gemini_response(combined_prompt, sys_prompt, api_key=api_keys.get('gemini'))
        send_log("Codebase generated. Writing files...")
        pattern = r"```([^\n]+)\n(.*?)```"
        matches = re.findall(pattern, raw_response, re.DOTALL)
        tag_fallbacks = {
            "python": "app.py",
            "py": "app.py",
            "html": "templates/index.html",
            "css": "static/style.css",
            "js": "static/script.js",
            "json": "config.json"
        }
        for raw_label, content in matches:
            label = raw_label.strip().split()[-1]
            fname = tag_fallbacks.get(label.lower(), label)
            path = os.path.normpath(os.path.join(proj_dir, fname))
            if path.startswith(proj_dir):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                send_log(f"Writing: {fname}")

        send_log(f"Starting server on port {port}...")
        python_bin = sys.executable or "python"
        proc = subprocess.Popen([python_bin, "app.py"], cwd=proj_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        proxy_url = f"/preview/{proj_id}/"
        RUNNING_APPS[proj_id] = {"url": proxy_url, "process": proc, "port": port}
        socketio.sleep(2)
        send_log(f"Server Active: {proxy_url}")
        send_log("Build completed!", redirect=True, project_id=proj_id, public_url=proxy_url)
    except Exception as e:
        send_log(f"Build failed: {str(e)}", status="error")

def restart_app(project_id):
    if project_id in RUNNING_APPS:
        try:
            RUNNING_APPS[project_id]["process"].terminate()
            RUNNING_APPS[project_id]["process"].wait(timeout=2)
        except Exception:
            pass
        port = RUNNING_APPS[project_id]["port"]
        proj_dir = os.path.join(WORKSPACE_ROOT, project_id)
        proc = subprocess.Popen([sys.executable, "app.py"], cwd=proj_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        RUNNING_APPS[project_id]["process"] = proc

@app.route('/api/projects/<proj_id>/url', methods=['GET'])
def get_project_url(proj_id):
    app_info = RUNNING_APPS.get(proj_id, {})
    return jsonify({"public_url": app_info.get("url", f"/preview/{proj_id}/")})

@app.route('/api/projects/<proj_id>/files', methods=['GET'])
def list_project_files(proj_id):
    proj_dir = os.path.normpath(os.path.join(WORKSPACE_ROOT, proj_id))
    if not proj_dir.startswith(WORKSPACE_ROOT) or not os.path.exists(proj_dir):
        return jsonify({"error": "Project not found"}), 404
    files = []
    for root, _, filenames in os.walk(proj_dir):
        for fname in filenames:
            rel = os.path.relpath(os.path.join(root, fname), proj_dir)
            files.append(rel.replace("\\", "/"))
    return jsonify(files)

@app.route('/api/projects/<proj_id>/files/<path:file_path>', methods=['GET', 'POST'])
def manage_file(proj_id, file_path):
    proj_dir = os.path.normpath(os.path.join(WORKSPACE_ROOT, proj_id))
    full_path = os.path.normpath(os.path.join(proj_dir, file_path))
    
    if not full_path.startswith(proj_dir):
        return jsonify({"error": "Unauthorized access"}), 403

    if request.method == 'GET':
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"content": content})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        data = request.get_json() or {}
        content = data.get('content', '')
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            if proj_id in RUNNING_APPS:
                restart_app(proj_id)
            return jsonify({"status": "saved"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
