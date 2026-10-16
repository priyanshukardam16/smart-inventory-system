import pandas as pd
import streamlit as st

from database import init_db, seed_sample_products
from inventory import get_products, add_product, update_product, restock_product, delete_product
from checkout import complete_sale
from reports import get_sales_summary, get_best_sellers, get_inventory_value
from ui import show_dashboard

st.set_page_config(page_title="Smart Inventory Manager", page_icon="📦", layout="wide")
init_db()
seed_sample_products()

st.markdown("""
<style>
    [data-testid="stSidebar"] { border-right: 1px solid rgba(128, 128, 128, 0.22); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 0.35rem 0.55rem; border-radius: 0.55rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(128, 128, 128, 0.12);
    }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 0.8rem; border-radius: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📦 StockSmart")
    st.caption("Inventory & order management")
    st.divider()
    page = st.radio(
        "WORKSPACE",
        ["🏠 Dashboard", "📦 Inventory", "📥 Restock", "🛒 Checkout", "📊 Sales Reports"],
    )
    st.divider()
    st.caption("Campus shop • Canteen • Club")

page = {
    "🏠 Dashboard": "Dashboard",
    "📦 Inventory": "Inventory",
    "📥 Restock": "Restock",
    "🛒 Checkout": "Checkout",
    "📊 Sales Reports": "Sales Reports",
}[page]

st.title("📦 Smart Inventory & Order Management")
st.caption("A simple inventory and checkout system for campus shops, canteens, and clubs.")

if page == "Dashboard":
    show_dashboard()

elif page == "Inventory":
    st.header("Product catalog")
    products = get_products()
    if not products.empty:
        st.dataframe(products[["id", "name", "category", "price", "stock", "reorder_level"]],
                     hide_index=True, use_container_width=True)
        st.download_button(
            "Download products as CSV",
            products.to_csv(index=False).encode("utf-8"),
            file_name="products.csv",
            mime="text/csv",
        )

    tab_add, tab_edit, tab_delete = st.tabs(["Add product", "Edit product", "Delete product"])

    with tab_add:
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("Product name")
            category = st.text_input("Category", value="General")
            price = st.number_input("Unit price (₹)", min_value=0.0, step=1.0, format="%.2f")
            stock = st.number_input("Opening stock", min_value=0, step=1)
            reorder = st.number_input("Minimum stock alert level", min_value=0, step=1, value=5)
            submitted = st.form_submit_button("Add product")
            if submitted:
                try:
                    add_product(name, category, price, stock, reorder)
                    st.success(f"Added {name.strip()} successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add product: {e}")

    with tab_edit:
        if products.empty:
            st.info("Add a product first.")
        else:
            options = {f'{r["name"]} (ID {int(r["id"])})': int(r["id"]) for _, r in products.iterrows()}
            selected_label = st.selectbox("Choose product to edit", list(options))
            selected_id = options[selected_label]
            selected = products[products["id"] == selected_id].iloc[0]
            with st.form("edit_product_form"):
                new_name = st.text_input("Name", value=str(selected["name"]))
                new_category = st.text_input("Category", value=str(selected["category"]))
                new_price = st.number_input("Unit price (₹)", min_value=0.0, value=float(selected["price"]), step=1.0)
                new_reorder = st.number_input("Reorder level", min_value=0, value=int(selected["reorder_level"]), step=1)
                if st.form_submit_button("Save changes"):
                    try:
                        update_product(selected_id, new_name, new_category, new_price, new_reorder)
                        st.success("Product updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update product: {e}")

    with tab_delete:
        if products.empty:
            st.info("There are no products to delete.")
        else:
            delete_options = {f'{r["name"]} (ID {int(r["id"])})': int(r["id"]) for _, r in products.iterrows()}
            delete_label = st.selectbox("Choose product to delete", list(delete_options), key="delete_product")
            confirm = st.checkbox("I understand this cannot be undone.")
            if st.button("Delete selected product", disabled=not confirm):
                try:
                    delete_product(delete_options[delete_label])
                    st.success("Product deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

elif page == "Restock":
    st.header("Record incoming stock")
    products = get_products()
    if products.empty:
        st.info("Add a product before restocking.")
    else:
        options = {f'{r["name"]} — current stock: {int(r["stock"])}': int(r["id"]) for _, r in products.iterrows()}
        with st.form("restock_form"):
            selected = st.selectbox("Product", list(options))
            quantity = st.number_input("Quantity to add", min_value=1, step=1)
            note = st.text_input("Note (optional)", value="Supplier restock")
            if st.form_submit_button("Record restock"):
                try:
                    restock_product(options[selected], int(quantity), note)
                    st.success("Stock updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not restock: {e}")

elif page == "Checkout":
    st.header("🛒 Checkout")
    products = get_products()
    available = products[products["stock"] > 0] if not products.empty else products

    if available.empty:
        st.info("No products are currently in stock.")
    else:
        st.caption("Select each product once, then set its quantity. This avoids duplicate-product quantity errors.")
        labels = {
            f'{r["name"]} — ₹{float(r["price"]):.2f} · {int(r["stock"])} available': int(r["id"])
            for _, r in available.iterrows()
        }
        selected_labels = st.multiselect(
            "Products in this order",
            options=list(labels.keys()),
            placeholder="Choose one or more products…",
            help="Each product can be selected only once. Select multiple different products for one sale.",
            key="checkout_selected_products",
        )

        cart = []
        subtotal_preview = 0.0
        if selected_labels:
            st.subheader("Order quantities")
            for label in selected_labels:
                product_id = labels[label]
                row = available.loc[available["id"] == product_id].iloc[0]
                stock_limit = int(row["stock"])
                quantity = st.number_input(
                    f'{row["name"]} — ₹{float(row["price"]):.2f} each',
                    min_value=1,
                    max_value=stock_limit,
                    value=1,
                    step=1,
                    key=f"checkout_qty_{product_id}",
                )
                cart.append({"product_id": product_id, "quantity": int(quantity)})
                subtotal_preview += float(row["price"]) * int(quantity)

        c1, c2 = st.columns(2)
        with c1:
            discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        with c2:
            tax = st.number_input("Tax (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

        discounted_preview = subtotal_preview * (1 - discount / 100)
        total_preview = discounted_preview * (1 + tax / 100)
        m1, m2 = st.columns(2)
        m1.metric("Subtotal", f"₹{subtotal_preview:,.2f}")
        m2.metric("Estimated total", f"₹{total_preview:,.2f}")
        st.caption("Tax is applied after discount. Confirm the applicable tax rate for your shop.")

        if st.button("✅ Complete sale", type="primary", disabled=not cart, use_container_width=True):
            try:
                sale = complete_sale(cart, discount, tax)
                receipt_lines = [
                    "SMART INVENTORY — RECEIPT",
                    f'Sale ID: {sale["sale_id"]}',
                    "",
                    "Item | Qty | Unit price | Line total",
                ]
                for pid, name, qty, unit_price, line_total in sale["items"]:
                    receipt_lines.append(f"{name} | {qty} | ₹{unit_price:.2f} | ₹{line_total:.2f}")
                receipt_lines += [
                    "",
                    f'Subtotal: ₹{sale["subtotal"]:.2f}',
                    f'Discount: {sale["discount_percent"]:.2f}%',
                    f'Tax: {sale["tax_percent"]:.2f}%',
                    f'TOTAL: ₹{sale["total"]:.2f}',
                    "Thank you!",
                ]
                st.session_state["latest_receipt"] = "\n".join(receipt_lines)
                st.session_state["latest_sale_id"] = sale["sale_id"]
                st.success(f'Sale #{sale["sale_id"]} completed. Stock has been updated.')
                st.rerun()
            except Exception as e:
                st.error(f"Checkout failed: {e}")

    if "latest_receipt" in st.session_state:
        st.subheader(f'Latest receipt — Sale #{st.session_state["latest_sale_id"]}')
        st.code(st.session_state["latest_receipt"])
        st.download_button(
            "⬇️ Download receipt (.txt)",
            st.session_state["latest_receipt"].encode("utf-8"),
            file_name=f'receipt_{st.session_state["latest_sale_id"]}.txt',
            mime="text/plain",
        )

elif page == "Sales Reports":
    st.header("Sales reports")
    sales = get_sales_summary()
    best = get_best_sellers()
    inventory_value = get_inventory_value()

    if sales.empty:
        st.info("No completed sales yet. Make a checkout to populate reports.")
    else:
        total_revenue = float(sales["total"].sum())
        st.metric("Total recorded revenue", f"₹{total_revenue:,.2f}")
        st.subheader("Sales history")
        st.dataframe(sales, hide_index=True, use_container_width=True)
        st.download_button("Download sales CSV", sales.to_csv(index=False).encode("utf-8"),
                           file_name="sales_report.csv", mime="text/csv")
        daily = sales.copy()
        daily["date"] = pd.to_datetime(daily["created_at"]).dt.date
        daily_totals = daily.groupby("date", as_index=False)["total"].sum()
        st.subheader("Revenue by date")
        st.bar_chart(daily_totals.set_index("date")["total"])

    st.subheader("Best-selling products")
    if best.empty:
        st.info("No sales items to rank yet.")
    else:
        st.dataframe(best, hide_index=True, use_container_width=True)
        st.download_button("Download best sellers CSV", best.to_csv(index=False).encode("utf-8"),
                           file_name="best_sellers.csv", mime="text/csv")

    st.subheader("Current inventory valuation")
    if inventory_value.empty:
        st.info("No products yet.")
    else:
        st.dataframe(inventory_value, hide_index=True, use_container_width=True)
        st.download_button("Download inventory valuation CSV",
                           inventory_value.to_csv(index=False).encode("utf-8"),
                           file_name="inventory_valuation.csv", mime="text/csv")
