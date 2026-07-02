# backend/routes/products.py
# Oliver's Seller Product Dashboard – API routes
# Stack: Python + Flask + SQLite

from flask import Blueprint, request, jsonify
import sqlite3
import os

products_bp = Blueprint('products', __name__)

# Path to the shared SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'app.db')


def get_db():
    """Open a database connection and return rows as dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us do row['name'] instead of row[0]
    return conn


def init_db():
    """Create tables and seed test data if they don't exist yet."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT    NOT NULL,
            email   TEXT    UNIQUE NOT NULL,
            role    TEXT    DEFAULT 'buyer'
        );

        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id   INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            description TEXT,
            price       REAL    NOT NULL,
            status      TEXT    DEFAULT 'Available',
            FOREIGN KEY (seller_id) REFERENCES users(id)
        );
    """)

    # Seed data – only insert if the table is empty
    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        cursor.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            ('Oliver', 'oliver@test.com', 'seller')
        )
        cursor.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            ('Alice', 'alice@test.com', 'buyer')
        )
        # Oliver's product listings
        products = [
            (1, 'Calculus Textbook', 'Good condition, minor highlights', 25.00, 'Available'),
            (1, 'Laptop Stand',      'Adjustable aluminium stand',       40.00, 'Sold'),
            (1, 'Scientific Calculator', 'Casio FX-991, barely used',   15.00, 'Available'),
        ]
        cursor.executemany(
            "INSERT INTO products (seller_id, name, description, price, status) VALUES (?,?,?,?,?)",
            products
        )

    conn.commit()
    conn.close()


# ─── ROUTES ──────────────────────────────────────────────────────────────────

# GET /api/products?seller_id=1
# Returns only the listings belonging to this seller
@products_bp.route('/api/products', methods=['GET'])
def get_products():
    seller_id = request.args.get('seller_id')
    if not seller_id:
        return jsonify({'error': 'seller_id query param is required'}), 400

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM products WHERE seller_id = ?", (seller_id,)
    ).fetchall()
    conn.close()

    # Convert sqlite3.Row objects to plain dicts so jsonify can serialise them
    return jsonify([dict(row) for row in rows])


# POST /api/products
# Add a new product listing
@products_bp.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    required = ('seller_id', 'name', 'price')

    if not all(data.get(k) for k in required):
        return jsonify({'error': 'seller_id, name, and price are required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (seller_id, name, description, price, status) VALUES (?,?,?,?,?)",
        (data['seller_id'], data['name'], data.get('description', ''), data['price'], 'Available')
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'id': new_id, 'message': 'Product listed!'}), 201


# PUT /api/products/<id>
# Edit an existing listing (name, description, price, or status)
@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()

    conn = get_db()
    conn.execute(
        "UPDATE products SET name=?, description=?, price=?, status=? WHERE id=?",
        (data['name'], data.get('description', ''), data['price'], data['status'], product_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'message': 'Product updated!'})


# DELETE /api/products/<id>
# Remove a listing
@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Product deleted!'})
