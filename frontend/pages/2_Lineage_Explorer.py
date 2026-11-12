import sys
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import APIClient

st.set_page_config(page_title="Lineage Explorer | Integration Hub", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .lineage-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        border-left: 4px solid #00897b;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-supplier { background-color: #e0f2f1; color: #004d40; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85em; }
    .badge-reason { background-color: #f1f8e9; color: #33691e; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Attribute-Level Lineage Explorer")
st.caption("Inspect exact source provenance, supplier priority rules, and fallback decisions for each attribute.")

products = APIClient.get("/api/products?limit=200") or []

if not products:
    st.info("No canonical products found. Please run the integration pipeline from the home page first.")
else:
    product_options = {
        f"{p['product_name']} ({p['brand']} | MPN: {p['manufacturer_part_number']})": p["product_id"]
        for p in products
    }
    selected_label = st.selectbox("Select a Product to Inspect Provenance:", list(product_options.keys()))
    selected_pid = product_options[selected_label]

    # Fetch lineage for this product
    lineage_entries = APIClient.get(f"/api/lineage/product/{selected_pid}") or []

    if lineage_entries:
        selected_prod = next((p for p in products if p["product_id"] == selected_pid), None)
        if selected_prod:
            st.markdown(
                f"**Canonical Product ID:** `{selected_pid}` &nbsp;|&nbsp; "
                f"**Contributing Suppliers:** `{selected_prod.get('source_suppliers')}` &nbsp;|&nbsp; "
                f"**Active Status:** `{selected_prod.get('status')}`"
            )

        st.subheader("Field-Level Provenance Decisions")
        
        # Display 3 cards per row
        cols = st.columns(3)
        for idx, entry in enumerate(lineage_entries):
            target_col = cols[idx % 3]
            with target_col:
                st.markdown(f"""
                <div class="lineage-card">
                    <span style="font-size: 0.75em; text-transform: uppercase; color: #666; font-weight: 600;">
                        Attribute: {entry['attribute_name']}
                    </span>
                    <h4 style="margin: 4px 0 6px 0; color: #111;">{entry['selected_value']}</h4>
                    <div style="margin-bottom: 4px;">
                        <strong>Source:</strong> <span class="badge-supplier">{entry['supplier_name']}</span>
                    </div>
                    <div style="font-size: 0.85em; color: #444; margin-bottom: 2px;">
                        <strong>Selection Rule:</strong> <span class="badge-reason">{entry['selection_reason']}</span>
                    </div>
                    <div style="font-size: 0.8em; color: #777;">
                        File: <code>{entry['source_file']}</code> (Record: {entry['source_record_id'] or 'N/A'})
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.subheader("Complete Lineage Audit Table")
        lineage_df = pd.DataFrame(lineage_entries)
        st.dataframe(lineage_df, use_container_width=True)
    else:
        st.warning("No lineage entries found for this product.")
