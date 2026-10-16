import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("inventory.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            category TEXT NOT NULL DEFAULT 'General',
            price REAL NOT NULL CHECK(price >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            reorder_level INTEGER NOT NULL DEFAULT 5 CHECK(reorder_level >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtotal REAL NOT NULL CHECK(subtotal >= 0),
            discount_percent REAL NOT NULL DEFAULT 0 CHECK(discount_percent BETWEEN 0 AND 100),
            tax_percent REAL NOT NULL DEFAULT 0 CHECK(tax_percent BETWEEN 0 AND 100),
            total REAL NOT NULL CHECK(total >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL REFERENCES sales(id),
            product_id INTEGER REFERENCES products(id),
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            line_total REAL NOT NULL CHECK(line_total >= 0)
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            movement_type TEXT NOT NULL CHECK(movement_type IN ('RESTOCK', 'SALE', 'ADJUSTMENT')),
            quantity_change INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

def seed_sample_products():
    samples = [
        ("Water Bottle", "Drinks", 20.00, 30, 8),
        ("Veg Sandwich", "Food", 50.00, 12, 5),
        ("Notebook", "Stationery", 45.00, 20, 6),
        ("Pen", "Stationery", 10.00, 50, 10),
        ("Chips", "Snacks", 20.00, 7, 10),
        ("Coffee", "Drinks", 30.00, 15, 5),
    ]
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO products(name, category, price, stock, reorder_level) VALUES (?, ?, ?, ?, ?)",
                samples,
            )
            conn.execute("""
                INSERT INTO stock_movements(product_id, movement_type, quantity_change, note)
                SELECT id, 'RESTOCK', stock, 'Initial sample stock'
                FROM products
            """)
