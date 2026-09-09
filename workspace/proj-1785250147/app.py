import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_NAME = 'inventory.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_email TEXT,
        phone TEXT
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        category_id INTEGER,
        supplier_id INTEGER,
        quantity INTEGER DEFAULT 0,
        min_stock_level INTEGER DEFAULT 5,
        unit_price REAL DEFAULT 0.0,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        movement_type TEXT CHECK(movement_type IN ('IN', 'OUT', 'ADJUSTMENT')) NOT NULL,
        quantity INTEGER NOT NULL,
        note TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO categories (name, description) VALUES ('Electronics', 'Gadgets and electronic components'), ('Office Supplies', 'Paper, pens, and desk items')")
        cursor.execute("INSERT INTO suppliers (name, contact_email, phone) VALUES ('TechSource Ltd', 'contact@techsource.com', '+1-555-0192'), ('Global Paper Co', 'sales@globalpaper.com', '+1-555-0143')")
        cursor.execute("INSERT INTO products (name, sku, category_id, supplier_id, quantity, min_stock_level, unit_price) VALUES ('Wireless Mouse', 'ELE-001', 1, 1, 15, 10, 25.99), ('Mechanical Keyboard', 'ELE-002', 1, 1, 3, 5, 89.99), ('A4 Printing Paper Pack', 'OFF-001', 2, 2, 45, 15, 12.50)")
        cursor.execute("INSERT INTO stock_movements (product_id, movement_type, quantity, note) VALUES (1, 'IN', 15, 'Initial Stock'), (2, 'IN', 3, 'Initial Stock'), (3, 'IN', 45, 'Initial Stock')")
    
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock_level")
    low_stock_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(quantity * unit_price) FROM products")
    total_value = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(*) FROM stock_movements")
    total_movements = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_value': round(total_value, 2),
        'total_movements': total_movements
    })

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, c.name as category_name, s.name as supplier_name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        ORDER BY p.id DESC
    ''')
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, c.name as category_name, s.name as supplier_name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = ?
    ''', (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, sku, category_id, supplier_id, quantity, min_stock_level, unit_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['sku'], data.get('category_id'), data.get('supplier_id'), 
              data.get('quantity', 0), data.get('min_stock_level', 5), data.get('unit_price', 0.0)))
        
        product_id = cursor.lastrowid
        
        if data.get('quantity', 0) > 0:
            cursor.execute('''
                INSERT INTO stock_movements (product_id, movement_type, quantity, note)
                VALUES (?, 'IN', ?, 'Initial Stock Entry')
            ''', (product_id, data['quantity']))
            
        conn.commit()
        conn.close()
        return jsonify({'message': 'Product added successfully', 'id': product_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'SKU must be unique'}), 400

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products 
        SET name=?, sku=?, category_id=?, supplier_id=?, min_stock_level=?, unit_price=?
        WHERE id=?
    ''', (data['name'], data['sku'], data.get('category_id'), data.get('supplier_id'),
          data.get('min_stock_level', 5), data.get('unit_price', 0.0), product_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Product updated successfully'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_movements WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Product deleted successfully'})

@app.route('/api/products/<int:product_id>/adjust', methods=['POST'])
def adjust_stock(product_id):
    data = request.json
    movement_type = data.get('movement_type')
    qty_change = int(data.get('quantity', 0))
    note = data.get('note', '')

    if movement_type not in ['IN', 'OUT', 'ADJUSTMENT'] or qty_change < 0:
        return jsonify({'error': 'Invalid movement parameters'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    
    if not prod:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404

    current_qty = prod['quantity']
    
    if movement_type == 'IN':
        new_qty = current_qty + qty_change
    elif movement_type == 'OUT':
        if current_qty < qty_change:
            conn.close()
            return jsonify({'error': 'Stock quantity cannot be negative'}), 400
        new_qty = current_qty - qty_change
    else:  # ADJUSTMENT
        new_qty = qty_change

    cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, product_id))
    cursor.execute('''
        INSERT INTO stock_movements (product_id, movement_type, quantity, note)
        VALUES (?, ?, ?, ?)
    ''', (product_id, movement_type, qty_change, note))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Stock updated successfully', 'new_quantity': new_qty})

@app.route('/api/categories', methods=['GET', 'POST'])
def manage_categories():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        try:
            cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", 
                           (data['name'], data.get('description', '')))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Category added'}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Category name already exists'}), 400
    
    cursor.execute("SELECT * FROM categories ORDER BY name ASC")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Category deleted'})

@app.route('/api/suppliers', methods=['GET', 'POST'])
def manage_suppliers():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO suppliers (name, contact_email, phone) VALUES (?, ?, ?)", 
                       (data['name'], data.get('contact_email', ''), data.get('phone', '')))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Supplier added'}), 201
    
    cursor.execute("SELECT * FROM suppliers ORDER BY name ASC")
    suppliers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(suppliers)

@app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Supplier deleted'})

@app.route('/api/movements', methods=['GET'])
def get_movements():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, p.name as product_name, p.sku 
        FROM stock_movements m
        JOIN products p ON m.product_id = p.id
        ORDER BY m.timestamp DESC
        LIMIT 100
    ''')
    movements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(movements)

@app.route('/api/notifications/low-stock', methods=['GET'])
def get_low_stock():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, c.name as category_name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.quantity <= p.min_stock_level
        ORDER BY p.quantity ASC
    ''')
    low_stock_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(low_stock_items)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
