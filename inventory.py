import pandas as pd
from database import get_connection

def get_products():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, name, category, price, stock, reorder_level, created_at
            FROM products ORDER BY name
        """).fetchall()
    return pd.DataFrame([dict(row) for row in rows],
                        columns=["id", "name", "category", "price", "stock", "reorder_level", "created_at"])

def add_product(name, category, price, stock, reorder_level):
    name = name.strip()
    category = category.strip() or "General"
    if not name:
        raise ValueError("Product name is required.")
    if price < 0 or stock < 0 or reorder_level < 0:
        raise ValueError("Price, stock, and reorder level cannot be negative.")
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO products(name, category, price, stock, reorder_level)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category, float(price), int(stock), int(reorder_level)))
        product_id = cur.lastrowid
        if stock:
            conn.execute("""
                INSERT INTO stock_movements(product_id, movement_type, quantity_change, note)
                VALUES (?, 'RESTOCK', ?, 'Opening stock')
            """, (product_id, int(stock)))
    return product_id

def update_product(product_id, name, category, price, reorder_level):
    name = name.strip()
    if not name:
        raise ValueError("Product name is required.")
    if price < 0 or reorder_level < 0:
        raise ValueError("Price and reorder level cannot be negative.")
    with get_connection() as conn:
        conn.execute("""
            UPDATE products
            SET name=?, category=?, price=?, reorder_level=?
            WHERE id=?
        """, (name, category.strip() or "General", float(price), int(reorder_level), int(product_id)))

def restock_product(product_id, quantity, note="Restock"):
    if quantity <= 0:
        raise ValueError("Restock quantity must be greater than zero.")
    with get_connection() as conn:
        cur = conn.execute("UPDATE products SET stock = stock + ? WHERE id=?", (int(quantity), int(product_id)))
        if cur.rowcount != 1:
            raise ValueError("Product not found.")
        conn.execute("""
            INSERT INTO stock_movements(product_id, movement_type, quantity_change, note)
            VALUES (?, 'RESTOCK', ?, ?)
        """, (int(product_id), int(quantity), note.strip() or "Restock"))

def delete_product(product_id):
    with get_connection() as conn:
        # Preserve historical sale records; products already sold cannot be deleted.
        used = conn.execute("SELECT 1 FROM sale_items WHERE product_id=? LIMIT 1", (int(product_id),)).fetchone()
        if used:
            raise ValueError("This product appears in sales history. Keep it to preserve reports.")
        conn.execute("DELETE FROM stock_movements WHERE product_id=?", (int(product_id),))
        cur = conn.execute("DELETE FROM products WHERE id=?", (int(product_id),))
        if cur.rowcount != 1:
            raise ValueError("Product not found.")
