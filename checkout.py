import sqlite3
from database import get_connection

def complete_sale(cart, discount_percent=0.0, tax_percent=0.0):
    """
    cart is a list of dicts: {"product_id": int, "quantity": int}
    All stock checks, stock reductions, and sale records are committed together.
    If any check fails, SQLite rolls back the whole checkout.
    """
    if not cart:
        raise ValueError("Your cart is empty.")
    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100%.")
    if not 0 <= tax_percent <= 100:
        raise ValueError("Tax must be between 0 and 100%.")

    # Combine duplicate product rows so the same item cannot bypass stock checks.
    quantities = {}
    for item in cart:
        pid = int(item["product_id"])
        qty = int(item["quantity"])
        if qty <= 0:
            raise ValueError("Every quantity must be at least 1.")
        quantities[pid] = quantities.get(pid, 0) + qty

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        lines = []
        subtotal = 0.0

        for pid, qty in quantities.items():
            product = conn.execute(
                "SELECT id, name, price, stock FROM products WHERE id=?", (pid,)
            ).fetchone()
            if product is None:
                raise ValueError(f"Product ID {pid} no longer exists.")
            if product["stock"] < qty:
                raise ValueError(
                    f"Not enough stock for {product['name']}. "
                    f"Available: {product['stock']}, requested: {qty}."
                )
            unit_price = float(product["price"])
            line_total = round(unit_price * qty, 2)
            subtotal += line_total
            lines.append((pid, product["name"], qty, unit_price, line_total))

        subtotal = round(subtotal, 2)
        discounted = round(subtotal * (1 - discount_percent / 100), 2)
        total = round(discounted * (1 + tax_percent / 100), 2)

        sale_cur = conn.execute("""
            INSERT INTO sales(subtotal, discount_percent, tax_percent, total)
            VALUES (?, ?, ?, ?)
        """, (subtotal, float(discount_percent), float(tax_percent), total))
        sale_id = sale_cur.lastrowid

        for pid, name, qty, unit_price, line_total in lines:
            # Conditional update is an additional guard against overselling.
            cur = conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (qty, pid, qty),
            )
            if cur.rowcount != 1:
                raise ValueError(f"Stock changed during checkout for {name}. Please try again.")
            conn.execute("""
                INSERT INTO sale_items(sale_id, product_id, product_name, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sale_id, pid, name, qty, unit_price, line_total))
            conn.execute("""
                INSERT INTO stock_movements(product_id, movement_type, quantity_change, note)
                VALUES (?, 'SALE', ?, ?)
            """, (pid, -qty, f"Sale #{sale_id}"))

        conn.commit()
        return {
            "sale_id": sale_id,
            "subtotal": subtotal,
            "discount_percent": float(discount_percent),
            "tax_percent": float(tax_percent),
            "total": total,
            "items": lines,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
