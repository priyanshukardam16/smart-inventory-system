import pandas as pd
import streamlit as st
from inventory import get_products

def show_dashboard():
    products = get_products()
    if products.empty:
        st.info("No products yet. Add your first product in Inventory.")
        return

    low = products[products["stock"] <= products["reorder_level"]]
    stock_value = float((products["price"] * products["stock"]).sum())

    with st.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("Products", len(products))
        c2.metric("Units in stock", int(products["stock"].sum()))
        c3.metric("Inventory value", f"₹{stock_value:,.2f}")

    st.subheader("Low-stock alerts")
    if low.empty:
        st.success("All products are above their reorder levels.")
    else:
        st.warning(f"{len(low)} product(s) need attention.")
        st.dataframe(low[["name", "category", "stock", "reorder_level"]], hide_index=True, use_container_width=True)

    st.subheader("Current inventory")
    display = products.copy()
    display["price"] = display["price"].map(lambda x: f"₹{x:,.2f}")
    st.dataframe(display[["id", "name", "category", "price", "stock", "reorder_level"]],
                 hide_index=True, use_container_width=True)
