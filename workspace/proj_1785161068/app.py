import os
import sqlite3
import base64
import datetime
import requests
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "copia-super-secret-key-2024")
DATABASE = "copia_store.db"

# M-Pesa Daraja Sandbox Configuration (Defaults provided for direct testing)
MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "uAc14TGEfN8jY2R05A51wXFvF13M4A2f")
MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "4AGiOAGkQ1NzA1Xg")
MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")
MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL", "https://mydomain.com/api/mpesa/callback")

# --- Database Helper Functions ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'customer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Products Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                image_url TEXT,
                stock INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Cart Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(product_id) REFERENCES products(id),
                UNIQUE(user_id, product_id)
            )
        ''')

        # Orders Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phone TEXT NOT NULL,
                delivery_location TEXT NOT NULL,
                total_amount REAL NOT NULL,
                payment_status TEXT DEFAULT 'PENDING',
                checkout_request_id TEXT UNIQUE,
                mpesa_receipt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Order Items Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')

        # Seed initial products if database is newly created
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            seed_products = [
                ("Solar Home System 200W", "Electronics", 18500.00, "Clean power system with 3 bulbs, phone charger, and solar panel.", "https://images.unsplash.com/photo-1509391365360-2e959784a276?w=500", 30),
                ("High Yield Maize Seed (10kg)", "Agriculture", 2400.00, "Certified drought-resistant hybrid maize seed for maximum yields.", "https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=500", 150),
                ("NPK Fertilizer 50kg Bag", "Agriculture", 3600.00, "Balanced soil nutrient blend for planting and top-dressing.", "https://images.unsplash.com/photo-1628352081506-83c43123ed6d?w=500", 100),
                ("Clean Cookstove (Energy Saving)", "Home Appliances", 4200.00, "Reduces charcoal consumption by 60% with smokeless technology.", "https://images.unsplash.com/photo-1584992236310-6edddc08acff?w=500", 40),
                ("Smart LED TV 32-Inch", "Electronics", 14500.00, "Low power consumption, HD resolution with solar battery compatibility.", "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=500", 25),
                ("5000 Litre Water Tank", "Construction", 38000.00, "Durable UV-stabilized plastic rain harvester storage tank.", "https://images.unsplash.com/photo-1542013936693-884638332954?w=500", 10),
                ("Backpack Crop Sprayer 16L", "Agriculture", 2800.00, "Ergonomic manual pump sprayer with brass adjustable nozzle.", "https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=500", 60),
                ("Copia Smartphone 4G", "Electronics", 7999.00, "Long-battery life Android phone optimized for mobile money apps.", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500", 80)
            ]
            cursor.executemany(
                "INSERT INTO products (name, category, price, description, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
                seed_products
            )
            
            # Default Admin User (phone: 0700000000, pass: admin123)
            cursor.execute(
                "INSERT INTO users (name, phone, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                ("Copia Admin", "0700000000", "admin@copia.co.ke", generate_password_hash("admin123"), "admin")
            )
            
        conn.commit()

# --- M-Pesa Daraja Integration Utilities ---
def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET), timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"M-Pesa Token Error: {e}")
    return None

def format_phone_number(phone):
    phone = phone.strip().replace("+", "").replace(" ", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("7") or phone.startswith("1"):
        return "254" + phone
    return phone

# --- Web Routes ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Authentication API ---
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")
    password = data.get("password")

    if not all([name, phone, password]):
        return jsonify({"error": "Name, phone, and password are required"}), 400

    phone = format_phone_number(phone)
    pwd_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, phone, email, password_hash) VALUES (?, ?, ?, ?)",
                (name, phone, email, pwd_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            session["user_id"] = user_id
            session["user_name"] = name
            session["role"] = "customer"
            
            return jsonify({"message": "Registration successful", "user": {"id": user_id, "name": name, "phone": phone, "role": "customer"}})
    except sqlite3.IntegrityError:
        return jsonify({"error": "A user with this phone number or email already exists"}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    phone = format_phone_number(data.get("phone", ""))
    password = data.get("password", "")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "phone": user["phone"],
                    "role": user["role"]
                }
            })
    
    return jsonify({"error": "Invalid phone number or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" in session:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, phone, email, role FROM users WHERE id = ?", (session["user_id"],))
            user = cursor.fetchone()
            if user:
                return jsonify({"user": dict(user)})
    return jsonify({"user": None})

# --- Product API ---
@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    query = "SELECT * FROM products"
    params = []
    
    if category and category != "All":
        query += " WHERE category = ?"
        params.append(category)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        
    return jsonify({"products": products})

@app.route("/api/products", methods=["POST"])
def add_product():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.json or {}
    name = data.get("name")
    category = data.get("category")
    price = float(data.get("price", 0))
    description = data.get("description", "")
    image_url = data.get("image_url", "https://images.unsplash.com/photo-1560393464-5c69a73c5770?w=500")
    stock = int(data.get("stock", 10))

    if not name or not category or price <= 0:
        return jsonify({"error": "Invalid product fields"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, category, price, description, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)",
            (name, category, price, description, image_url, stock)
        )
        conn.commit()
        return jsonify({"message": "Product added successfully", "id": cursor.lastrowid})

# --- Cart API ---
@app.route("/api/cart", methods=["GET", "POST", "PUT", "DELETE"])
def cart_operations():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    with get_db() as conn:
        cursor = conn.cursor()

        if request.method == "GET":
            cursor.execute('''
                SELECT c.id as cart_id, c.quantity, p.id as product_id, p.name, p.price, p.image_url, p.category
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = ?
            ''', (user_id,))
            cart_items = [dict(row) for row in cursor.fetchall()]
            total = sum(item["price"] * item["quantity"] for item in cart_items)
            return jsonify({"cart": cart_items, "total": total})

        elif request.method == "POST":
            data = request.json or {}
            product_id = data.get("product_id")
            quantity = int(data.get("quantity", 1))

            cursor.execute("SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
            existing = cursor.fetchone()

            if existing:
                new_qty = existing["quantity"] + quantity
                cursor.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
            else:
                cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))

            conn.commit()
            return jsonify({"message": "Item added to cart"})

        elif request.method == "PUT":
            data = request.json or {}
            cart_id = data.get("cart_id")
            quantity = int(data.get("quantity", 1))

            if quantity <= 0:
                cursor.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_id, user_id))
            else:
                cursor.execute("UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?", (quantity, cart_id, user_id))

            conn.commit()
            return jsonify({"message": "Cart updated"})

        elif request.method == "DELETE":
            cart_id = request.args.get("cart_id")
            if cart_id:
                cursor.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_id, user_id))
            else:
                cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
            conn.commit()
            return jsonify({"message": "Cart cleared"})

# --- M-Pesa & Order Checkout API ---
@app.route("/api/checkout/mpesa", methods=["POST"])
def mpesa_checkout():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json or {}
    phone = format_phone_number(data.get("phone", ""))
    delivery_location = data.get("delivery_location", "Local Copia Agent Center")

    if not phone:
        return jsonify({"error": "Valid M-Pesa phone number is required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Calculate Total
        cursor.execute('''
            SELECT c.quantity, p.id, p.price, p.stock 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        ''', (user_id,))
        items = cursor.fetchall()

        if not items:
            return jsonify({"error": "Your cart is empty"}), 400

        total_amount = sum(item["price"] * item["quantity"] for item in items)
        
        # Generate STK Push timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password_b64 = base64.b64encode(password_str.encode()).decode('utf-8')

        access_token = get_mpesa_access_token()
        
        checkout_request_id = f"WS_REQ_{int(datetime.datetime.now().timestamp()*1000)}"
        
        # Attempt Real Daraja STK Push if token is valid
        stk_success = False
        if access_token:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "BusinessShortCode": MPESA_SHORTCODE,
                "Password": password_b64,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(total_amount),
                "PartyA": phone,
                "PartyB": MPESA_SHORTCODE,
                "PhoneNumber": phone,
                "CallBackURL": MPESA_CALLBACK_URL,
                "AccountReference": f"COPIA_{user_id}",
                "TransactionDesc": "Copia Goods Order"
            }
            try:
                res = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers=headers, timeout=10)
                res_data = res.json()
                if res_data.get("ResponseCode") == "0":
                    checkout_request_id = res_data.get("CheckoutRequestID")
                    stk_success = True
            except Exception as e:
                print(f"STK Push API Call failed: {e}")

        # Create Pending Order in Database
        cursor.execute('''
            INSERT INTO orders (user_id, phone, delivery_location, total_amount, payment_status, checkout_request_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, phone, delivery_location, total_amount, 'PENDING', checkout_request_id))
        
        order_id = cursor.lastrowid

        # Move cart items to order_items
        for item in items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, price, quantity)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item["id"], item["price"], item["quantity"]))

        # Clear Cart
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()

        return jsonify({
            "message": "STK Push initiated successfully on your phone.",
            "order_id": order_id,
            "checkout_request_id": checkout_request_id,
            "stk_pushed": stk_success,
            "simulated": not stk_success
        })

@app.route("/api/mpesa/stk_status/<checkout_id>", methods=["GET"])
def check_stk_status(checkout_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, payment_status, mpesa_receipt FROM orders WHERE checkout_request_id = ?", (checkout_id,))
        order = cursor.fetchone()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "order_id": order["id"],
            "status": order["payment_status"],
            "receipt": order["mpesa_receipt"]
        })

@app.route("/api/mpesa/simulate_payment", methods=["POST"])
def simulate_mpesa_payment():
    """Allows testing/simulating immediate M-Pesa payment completion without live Daraja callbacks"""
    data = request.json or {}
    checkout_id = data.get("checkout_request_id")
    
    if not checkout_id:
        return jsonify({"error": "Checkout ID required"}), 400

    receipt = f"QHK{datetime.datetime.now().strftime('%H%M%S')}CP"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders 
            SET payment_status = 'PAID', mpesa_receipt = ? 
            WHERE checkout_request_id = ?
        ''', (receipt, checkout_id))
        conn.commit()

    return jsonify({"message": "Payment simulation successful", "status": "PAID", "receipt": receipt})

@app.route("/api/mpesa/callback", methods=["POST"])
def mpesa_callback():
    """Daraja API Webhook Callback"""
    callback_data = request.json or {}
    print("M-Pesa Callback Data:", callback_data)

    try:
        stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        checkout_id = stk_callback.get("CheckoutRequestID")

        if result_code == 0:
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            receipt = ""
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt = item.get("Value")

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders 
                    SET payment_status = 'PAID', mpesa_receipt = ? 
                    WHERE checkout_request_id = ?
                ''', (receipt, checkout_id))
                conn.commit()
    except Exception as e:
        print(f"Error handling M-Pesa callback: {e}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route("/api/orders", methods=["GET"])
def get_user_orders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        orders = [dict(row) for row in cursor.fetchall()]

        for order in orders:
            cursor.execute('''
                SELECT oi.quantity, oi.price, p.name, p.image_url 
                FROM order_items oi 
                JOIN products p ON oi.product_id = p.id 
                WHERE oi.order_id = ?
            ''', (order["id"],))
            order["items"] = [dict(i) for i in cursor.fetchall()]

    return jsonify({"orders": orders})

@app.route("/api/admin/orders", methods=["GET"])
def get_all_orders():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, u.name as customer_name 
            FROM orders o 
            JOIN users u ON o.user_id = u.id 
            ORDER BY o.created_at DESC
        ''')
        orders = [dict(row) for row in cursor.fetchall()]

    return jsonify({"orders": orders})

if __name__ == "__main__":
    init_db()
    print("Copia E-Commerce Platform Server running on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)