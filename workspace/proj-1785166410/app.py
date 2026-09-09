import sqlite3
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, g, session

app = Flask(__name__)
app.secret_key = 'super_secret_captive_portal_key'
DATABASE = 'captive_portal.db'

# -------------------------------------------------------------------
# Database Setup & Helpers
# -------------------------------------------------------------------
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
        
        # Table for Vouchers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                duration_minutes INTEGER NOT NULL,
                is_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for Active/Past User Sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                mac_address TEXT,
                ip_address TEXT,
                user_email TEXT,
                voucher_code TEXT,
                zone_id TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            )
        ''')
        
        # Table for Access Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seed default vouchers if empty
        cursor.execute("SELECT COUNT(*) as count FROM vouchers")
        if cursor.fetchone()['count'] == 0:
            sample_vouchers = [
                ('WIFI-1001', 30),
                ('WIFI-1002', 60),
                ('GUEST-VIP', 120),
                ('FREE-PASS', 15)
            ]
            cursor.executemany("INSERT INTO vouchers (code, duration_minutes) VALUES (?, ?)", sample_vouchers)
        
        db.commit()

init_db()

def log_event(session_id, action):
    db = get_db()
    db.execute("INSERT INTO access_logs (session_id, action) VALUES (?, ?)", (session_id, action))
    db.commit()

# -------------------------------------------------------------------
# Routes & Controllers
# -------------------------------------------------------------------

@app.route('/')
def root():
    # Simulate router redirecting standard traffic to portal zone
    user_mac = request.args.get('mac', 'AA:BB:CC:DD:EE:FF')
    user_ip = request.args.get('ip', request.remote_addr or '192.168.1.105')
    return redirect(url_for('portal_landing', zone_id='zone-lobby', mac=user_mac, ip=user_ip))

# Dynamic Dynamic Route for Portal Zones
@app.route('/portal/<zone_id>', methods=['GET'])
def portal_landing(zone_id):
    mac = request.args.get('mac', '00:11:22:33:44:55')
    ip = request.args.get('ip', '192.168.1.50')
    
    # Check if MAC already has an active session
    db = get_db()
    now = datetime.now()
    cursor = db.execute(
        "SELECT * FROM sessions WHERE mac_address = ? AND status = 'ACTIVE' AND expires_at > ?", 
        (mac, now)
    )
    active_session = cursor.fetchone()
    
    if active_session:
        return redirect(url_for('session_status', session_id=active_session['id']))
        
    zones_info = {
        'zone-lobby': {'name': 'Main Lobby Guest Wi-Fi', 'speed': '10 Mbps', 'limit': '30 Mins Free'},
        'zone-cafe': {'name': 'Cafeteria High-Speed Pass', 'speed': '50 Mbps', 'limit': 'Voucher Required'},
        'zone-conference': {'name': 'Executive Lounge', 'speed': '100 Mbps', 'limit': 'Unlimited Access'}
    }
    
    current_zone = zones_info.get(zone_id, {'name': f'Zone {zone_id.upper()}', 'speed': '15 Mbps', 'limit': 'Standard Guest Access'})
    
    return render_template('index.html', zone_id=zone_id, zone=current_zone, mac=mac, ip=ip)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/login', methods=['POST'])
def process_login():
    auth_type = request.form.get('auth_type')
    zone_id = request.form.get('zone_id', 'zone-lobby')
    mac = request.form.get('mac', '00:00:00:00:00:00')
    ip = request.form.get('ip', request.remote_addr)
    
    db = get_db()
    duration_mins = 30
    user_email = None
    voucher_code = None
    
    if auth_type == 'voucher':
        voucher_code = request.form.get('voucher_code', '').strip().upper()
        cursor = db.execute("SELECT * FROM vouchers WHERE code = ? AND is_used = 0", (voucher_code,))
        voucher = cursor.fetchone()
        
        if not voucher:
            return render_template('index.html', 
                                   zone_id=zone_id, 
                                   zone={'name': f'Zone {zone_id}', 'speed': 'Standard', 'limit': 'N/A'},
                                   mac=mac, ip=ip, 
                                   error="Invalid or already used voucher code.")
        
        duration_mins = voucher['duration_minutes']
        db.execute("UPDATE vouchers SET is_used = 1 WHERE id = ?", (voucher['id'],))
        
    elif auth_type == 'email':
        user_email = request.form.get('email', '').strip()
        tos_accepted = request.form.get('terms_accepted')
        
        if not user_email or not tos_accepted:
            return render_template('index.html', 
                                   zone_id=zone_id, 
                                   zone={'name': f'Zone {zone_id}', 'speed': 'Standard', 'limit': 'N/A'},
                                   mac=mac, ip=ip, 
                                   error="Please provide a valid email and accept the Terms of Service.")
        duration_mins = 45 # Default free email tier duration
    
    else:
        return redirect(url_for('portal_landing', zone_id=zone_id))

    # Generate Session ID
    session_id = 'SESS-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    now = datetime.now()
    expires_at = now + timedelta(minutes=duration_mins)
    
    db.execute(
        """INSERT INTO sessions (id, mac_address, ip_address, user_email, voucher_code, zone_id, start_time, expires_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')""",
        (session_id, mac, ip, user_email, voucher_code, zone_id, now, expires_at)
    )
    db.commit()
    log_event(session_id, f"ACCESS_GRANTED via {auth_type.upper()}")
    
    return redirect(url_for('session_status', session_id=session_id))

# Dynamic Route for Session Status & Timer
@app.route('/status/<session_id>')
def session_status(session_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    user_session = cursor.fetchone()
    
    if not user_session:
        return redirect(url_for('root'))
    
    now = datetime.now()
    expires_at = datetime.strptime(user_session['expires_at'], '%Y-%m-%d %H:%M:%S.%f') if '.' in user_session['expires_at'] else datetime.strptime(user_session['expires_at'], '%Y-%m-%d %H:%M:%S')
    
    remaining_seconds = max(0, int((expires_at - now).total_seconds()))
    is_expired = remaining_seconds <= 0
    
    if is_expired and user_session['status'] == 'ACTIVE':
        db.execute("UPDATE sessions SET status = 'EXPIRED' WHERE id = ?", (session_id,))
        db.commit()
        log_event(session_id, "SESSION_EXPIRED")
    
    return render_template('status.html', session=user_session, remaining_seconds=remaining_seconds, is_expired=is_expired)

@app.route('/disconnect/<session_id>', methods=['POST'])
def disconnect(session_id):
    db = get_db()
    db.execute("UPDATE sessions SET status = 'DISCONNECTED' WHERE id = ?", (session_id,))
    db.commit()
    log_event(session_id, "USER_DISCONNECTED")
    return redirect(url_for('root'))

# API Route for Voucher Pre-validation (AJAX dynamic check)
@app.route('/api/validate-voucher/<code>', methods=['GET'])
def validate_voucher(code):
    db = get_db()
    cursor = db.execute("SELECT duration_minutes, is_used FROM vouchers WHERE code = ?", (code.upper(),))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'valid': False, 'message': 'Voucher code does not exist.'})
    if row['is_used'] == 1:
        return jsonify({'valid': False, 'message': 'Voucher has already been redeemed.'})
        
    return jsonify({'valid': True, 'duration': row['duration_minutes'], 'message': f'Valid code! Grants {row["duration_minutes"]} mins.'})

# Admin Dashboard Route
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    db = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generate_voucher':
            duration = int(request.form.get('duration', 60))
            code = 'GUEST-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            db.execute("INSERT INTO vouchers (code, duration_minutes) VALUES (?, ?)", (code, duration))
            db.commit()
            
    vouchers = db.execute("SELECT * FROM vouchers ORDER BY id DESC LIMIT 20").fetchall()
    active_sessions = db.execute("SELECT * FROM sessions WHERE status = 'ACTIVE' ORDER BY start_time DESC").fetchall()
    logs = db.execute("SELECT * FROM access_logs ORDER BY id DESC LIMIT 15").fetchall()
    
    return render_template('admin.html', vouchers=vouchers, active_sessions=active_sessions, logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
