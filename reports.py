import pandas as pd
from database import get_connection

def get_sales_summary():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id AS sale_id, subtotal, discount_percent, tax_percent, total, created_at
            FROM sales ORDER BY id DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows],
                        columns=["sale_id", "subtotal", "discount_percent", "tax_percent", "total", "created_at"])

def get_best_sellers():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT product_name, SUM(quantity) AS units_sold, ROUND(SUM(line_total), 2) AS sales_value
            FROM sale_items
            GROUP BY product_name
            ORDER BY units_sold DESC, sales_value DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows],
                        columns=["product_name", "units_sold", "sales_value"])

def get_inventory_value():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT name, category, price, stock, ROUND(price * stock, 2) AS inventory_value,
                   reorder_level
            FROM products ORDER BY inventory_value DESC
        """).fetchall()
    return pd.DataFrame([dict(r) for r in rows],
                        columns=["name", "category", "price", "stock", "inventory_value", "reorder_level"])
