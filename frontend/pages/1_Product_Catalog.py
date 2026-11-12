import sys
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import APIClient, BACKEND_URL

st.set_page_config(page_title="Product Catalog | Integration Hub", page_icon="📦", layout="wide")

st.title("📦 Canonical Product Catalog")
st.caption("Standardized golden records unified across all supplier feeds.")

# Fetch statistics for filter dropdowns
stats = APIClient.get("/api/products/summary/stats") or {}
brands = ["All"] + stats.get("brands", [])
categories = ["All"] + stats.get("categories", [])

# Filter Controls
fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
with fcol1:
    search_term = st.text_input("🔍 Search Catalog (Name, GTIN, Brand, or MPN)", "")
with fcol2:
    selected_brand = st.selectbox("Filter Brand", brands)
with fcol3:
    selected_category = st.selectbox("Filter Category", categories)

# Fetch filtered products from API
params = {"limit": 500}
if search_term.strip():
    params["search"] = search_term.strip()
if selected_brand != "All":
    params["brand"] = selected_brand
if selected_category != "All":
    params["category"] = selected_category

products = APIClient.get("/api/products", params=params)

if products:
    df = pd.DataFrame(products)
    st.write(f"Showing **{len(df)}** canonical products")

    display_cols = [
        "product_id", "gtin", "brand", "manufacturer_part_number", "product_name",
        "price", "currency", "stock_quantity", "category", "source_suppliers", "status", "updated_at"
    ]
    # Filter columns that exist
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        column_config={
            "price": st.column_config.NumberColumn("Price (USD)", format="$%.2f"),
            "stock_quantity": st.column_config.NumberColumn("Stock Qty"),
            "product_id": st.column_config.TextColumn("Canonical Product ID", width="small"),
            "source_suppliers": st.column_config.TextColumn("Contributors"),
            "updated_at": st.column_config.DatetimeColumn("Last Updated", format="YYYY-MM-DD HH:mm:ss")
        }
    )

    # Download Buttons (CSV and Excel .xlsx)
    import io

    csv_bytes = df[display_cols].to_csv(index=False).encode("utf-8")
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df[display_cols].to_excel(writer, index=False, sheet_name="Canonical Catalog")
    excel_bytes = excel_buffer.getvalue()

    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.download_button(
            "📥 Download Filtered Catalog (CSV)",
            csv_bytes,
            "canonical_product_catalog.csv",
            "text/csv",
            use_container_width=True
        )
    with dcol2:
        st.download_button(
            "📊 Download Filtered Catalog (Excel .xlsx)",
            excel_bytes,
            "canonical_product_catalog.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    st.info("No products match the selected criteria or the catalog is empty. Click 'Run Full Integration Pipeline' on the homepage.")
