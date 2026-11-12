import sys
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import APIClient

st.set_page_config(page_title="Run Metrics | Integration Hub", page_icon="📊", layout="wide")

st.title("📊 Observability & Pipeline Execution Metrics")
st.caption("Operational telemetry, execution latencies, and source-to-target mathematical reconciliation.")

runs = APIClient.get("/api/metrics/runs?limit=50") or []
recon = APIClient.get("/api/metrics/reconciliation") or {}

# Top Reconciliation Section
st.subheader("Source-to-Target Mathematical Reconciliation")
if recon and recon.get("reconciled"):
    st.success(
        f"✅ **Reconciliation Passed (100% Data Quality Integrity)**\n\n"
        f"**Assertion**: `{recon.get('reconciliation_formula')}`"
    )
elif recon and not recon.get("reconciled") and recon.get("status") != "NO_RUNS":
    st.error("❌ **Reconciliation Discrepancy Detected!** Total input records do not balance with outputs.")
else:
    st.info("No pipeline executions logged yet.")

st.divider()

# Historical Pipeline Runs
st.subheader("Historical Execution Runs")
if runs:
    rdf = pd.DataFrame(runs)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Executions Logged", len(rdf))
    m2.metric("Successful Runs", len(rdf[rdf["status"] == "SUCCESS"]))
    avg_latency = rdf["run_duration_sec"].mean()
    m3.metric("Average Latency", f"{avg_latency:.3f}s")
    latest_canonical = rdf.iloc[0]["canonical_products_count"]
    m4.metric("Latest Golden Products", latest_canonical)

    display_cols = [
        "run_id", "status", "started_at", "run_duration_sec",
        "total_input_rows", "valid_rows", "rejected_rows", "canonical_products_count", "reconciliation_passed"
    ]
    display_cols = [c for c in display_cols if c in rdf.columns]

    st.dataframe(
        rdf[display_cols],
        use_container_width=True,
        column_config={
            "run_duration_sec": st.column_config.NumberColumn("Latency (s)", format="%.3f"),
            "started_at": st.column_config.DatetimeColumn("Started At", format="YYYY-MM-DD HH:mm:ss"),
            "reconciliation_passed": st.column_config.CheckboxColumn("Reconciled?")
        }
    )

    # Bar chart of Ingested vs Valid vs Quarantined
    st.subheader("Processing Volume Trends")
    chart_df = rdf[["run_id", "valid_rows", "rejected_rows"]].set_index("run_id").head(10)
    st.bar_chart(chart_df)
else:
    st.info("No runs available to show.")
