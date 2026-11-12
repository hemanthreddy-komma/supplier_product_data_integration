import json
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import APIClient

st.set_page_config(page_title="Quarantine | Integration Hub", page_icon="⚠️", layout="wide")

st.title("⚠️ Quarantined Records Store")
st.caption("Records isolated during pipeline validation with detailed diagnostic failure reasons.")

quarantined = APIClient.get("/api/metrics/quarantine?limit=200") or []
reasons = APIClient.get("/api/metrics/quarantine/reasons") or []

if not quarantined:
    st.success("🎉 Quarantine store is currently empty! All incoming supplier records passed validation.")
else:
    # Summary of Rejection Reasons
    st.subheader("Data Quality Failure Breakdown")
    rcol1, rcol2 = st.columns([1, 2])
    with rcol1:
        if reasons:
            rdf = pd.DataFrame(reasons)
            st.dataframe(rdf, use_container_width=True)
    with rcol2:
        st.info(
            f"**Total Quarantined:** {len(quarantined)} records\n\n"
            "Records are quarantined whenever they violate business rules such as missing mandatory names, "
            "negative price/stock, invalid GS1 check-digits, or missing all primary and fallback identifiers."
        )

    st.divider()

    # Quarantined Table
    st.subheader("Quarantined Records Register")
    q_df = pd.DataFrame(quarantined)
    
    display_cols = ["quarantine_id", "supplier_id", "source_file", "rejection_reason", "quarantined_at"]
    st.dataframe(
        q_df[display_cols],
        use_container_width=True,
        column_config={
            "quarantine_id": st.column_config.TextColumn("Quarantine ID", width="small"),
            "rejection_reason": st.column_config.TextColumn("Diagnostic Reason", width="large"),
            "quarantined_at": st.column_config.DatetimeColumn("Quarantined At", format="YYYY-MM-DD HH:mm:ss")
        }
    )

    st.divider()

    # Raw Payload Inspector
    st.subheader("Raw Source Payload Inspector")
    qid_options = [q["quarantine_id"] for q in quarantined]
    selected_qid = st.selectbox("Select Quarantine ID to Inspect Original Payload:", qid_options)

    selected_record = next((q for q in quarantined if q["quarantine_id"] == selected_qid), None)
    if selected_record:
        st.markdown(f"**Diagnostic Error:** `{selected_record['rejection_reason']}`")
        st.markdown(f"**Source File:** `{selected_record['source_file']}` (Supplier: `{selected_record['supplier_id']}`)")
        
        raw_payload = selected_record.get("raw_payload", {})
        if isinstance(raw_payload, str):
            try:
                raw_payload = json.loads(raw_payload)
            except Exception:
                pass

        icol1, icol2 = st.columns([1, 1])
        with icol1:
            st.markdown("##### 🔍 Original Payload")
            if isinstance(raw_payload, dict):
                st.json(raw_payload)
            else:
                st.code(str(raw_payload))

        with icol2:
            st.markdown("##### 🛠️ Fix & Remediate Record")
            st.caption("Edit the faulty fields below (e.g. correct check-digit or fix negative price) and re-ingest.")
            
            payload_str = json.dumps(raw_payload, indent=2) if isinstance(raw_payload, dict) else str(raw_payload)
            edited_payload_str = st.text_area(
                "Corrected JSON Payload:",
                value=payload_str,
                height=220,
                key=f"edit_{selected_qid}"
            )

            if st.button("🚀 Re-Validate & Merge into Catalog", key=f"btn_fix_{selected_qid}", use_container_width=True):
                try:
                    corrected_json = json.loads(edited_payload_str)
                    res = APIClient.post(f"/api/metrics/quarantine/{selected_qid}/reprocess", data=corrected_json)
                    if res and res.get("success"):
                        st.success(res.get("message", "Record successfully remediated!"))
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(res.get("message", "Validation failed on corrected payload."))
                except json.JSONDecodeError as jde:
                    st.error(f"Invalid JSON syntax: {jde}")
                except Exception as ex:
                    st.error(f"Remediation error: {ex}")
