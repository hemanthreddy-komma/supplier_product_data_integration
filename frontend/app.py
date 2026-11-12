import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import APIClient


st.set_page_config(
    page_title="Supplier Hub | Data Integration",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# CUSTOM THEME
# --------------------------------------------------

st.markdown("""
<style>

/* Global */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #f5f7fb;
}

/* Hide Streamlit branding */
#MainMenu, footer {
    visibility: hidden;
}

/* Main content */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #101a33 0%, #17294a 100%);
}

[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 8px;
}

[data-testid="stSidebar"] .stButton button {
    border-radius: 9px;
    font-weight: 600;
}

/* Hero */
.hero {
    background: linear-gradient(120deg, #14213d 0%, #253e70 55%, #4263b5 100%);
    padding: 30px 34px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 8px 25px rgba(28, 48, 91, 0.15);
}

.hero h1 {
    color: white;
    font-size: 29px;
    font-weight: 800;
    margin: 0 0 8px 0;
}

.hero p {
    color: #dbeafe;
    font-size: 14px;
    margin: 0;
}

.hero-tag {
    display: inline-block;
    margin-top: 18px;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.2);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* KPI cards */
.kpi-card {
    background: white;
    border: 1px solid #e8edf5;
    border-radius: 15px;
    padding: 19px;
    min-height: 125px;
    box-shadow: 0 3px 12px rgba(25, 42, 70, 0.04);
}

.kpi-label {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 12px;
}

.kpi-value {
    color: #172554;
    font-size: 27px;
    font-weight: 800;
    letter-spacing: -1px;
}

.kpi-icon {
    font-size: 20px;
    margin-bottom: 8px;
}

/* Section headings */
.section-title {
    color: #172554;
    font-size: 19px;
    font-weight: 750;
    margin-top: 25px;
    margin-bottom: 5px;
}

.section-subtitle {
    color: #64748b;
    font-size: 12px;
    margin-bottom: 17px;
}

/* Workspace cards */
.workspace-card {
    background: white;
    border: 1px solid #e8edf5;
    border-radius: 14px;
    padding: 20px;
    min-height: 145px;
    box-shadow: 0 3px 12px rgba(25, 42, 70, 0.035);
}

.workspace-icon {
    font-size: 25px;
    margin-bottom: 12px;
}

.workspace-title {
    color: #172554;
    font-size: 14px;
    font-weight: 750;
    margin-bottom: 6px;
}

.workspace-description {
    color: #64748b;
    font-size: 12px;
    line-height: 1.6;
}

/* Supplier status */
.supplier-card {
    background: white;
    border: 1px solid #e8edf5;
    border-radius: 12px;
    padding: 14px 17px;
    margin-bottom: 10px;
}

.supplier-name {
    color: #172554;
    font-weight: 700;
    font-size: 13px;
}

.supplier-meta {
    color: #64748b;
    font-size: 11px;
    margin-top: 4px;
}

.priority {
    background: #eaf1ff;
    color: #2454a6;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}

/* Buttons */
.stButton button {
    border-radius: 9px;
    font-weight: 650;
    min-height: 42px;
}

/* Tables */
[data-testid="stDataFrame"] {
    border: 1px solid #e8edf5;
    border-radius: 12px;
    overflow: hidden;
}

/* Reconciliation */
.audit-ok {
    background: #eaf8f0;
    border: 1px solid #b9e8ca;
    color: #166534;
    padding: 15px 18px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
}

.audit-error {
    background: #fff0f0;
    border: 1px solid #fecaca;
    color: #b91c1c;
    padding: 15px 18px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# REUSABLE UI COMPONENTS
# --------------------------------------------------

def section_heading(title, subtitle=None):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )

    if subtitle:
        st.markdown(
            f'<div class="section-subtitle">{subtitle}</div>',
            unsafe_allow_html=True
        )


def metric_card(icon, label, value):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def workspace_card(icon, title, description):
    st.markdown(f"""
    <div class="workspace-card">
        <div class="workspace-icon">{icon}</div>
        <div class="workspace-title">{title}</div>
        <div class="workspace-description">{description}</div>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.markdown("""
<div style="padding: 10px 0 22px 0;">
    <div style="font-size:27px;">📦</div>
    <div style="font-size:19px;font-weight:800;">SUPPLIER HUB</div>
    <div style="font-size:10px;color:#a9bbd9;">
        DATA INTEGRATION PLATFORM
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()

st.sidebar.markdown("### ⚙️ Pipeline Controls")

# Supplier configuration
st.sidebar.markdown("#### 🏆 Supplier Priorities")

suppliers = APIClient.get("/api/uploads/suppliers")

if suppliers:
    for supplier in suppliers:
        st.sidebar.markdown(
            f"""
            <div style="
                background:rgba(255,255,255,0.07);
                padding:10px;
                border-radius:9px;
                margin-bottom:8px;
                border:1px solid rgba(255,255,255,0.10);
            ">
                <div style="font-weight:700;font-size:12px;">
                    Priority {supplier['priority']} · {supplier['supplier_id']}
                </div>
                <div style="font-size:11px;color:#bdcce3;">
                    {supplier['name']}
                </div>
                <div style="font-size:10px;color:#9db2d2;">
                    Format: {supplier['default_format'].upper()}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.sidebar.caption("Supplier configuration unavailable.")

st.sidebar.divider()

# Upload controls
st.sidebar.markdown("#### 📤 Upload Supplier Feeds")

up_a = st.sidebar.file_uploader(
    "Supplier A · JSON / Excel",
    type=["json", "xlsx", "xls", "csv"],
    key="up_a"
)

if up_a and st.sidebar.button(
    "Upload Supplier A",
    key="btn_up_a",
    use_container_width=True
):
    with st.spinner("Uploading Supplier A..."):
        res = APIClient.upload_file(
            "/api/uploads/supplier_a",
            up_a.getvalue(),
            up_a.name
        )

        if res:
            st.sidebar.success(
                f"Uploaded {res.get('record_count', 0)} records"
            )

up_b = st.sidebar.file_uploader(
    "Supplier B · CSV / Excel",
    type=["csv", "xlsx", "xls", "json"],
    key="up_b"
)

if up_b and st.sidebar.button(
    "Upload Supplier B",
    key="btn_up_b",
    use_container_width=True
):
    with st.spinner("Uploading Supplier B..."):
        res = APIClient.upload_file(
            "/api/uploads/supplier_b",
            up_b.getvalue(),
            up_b.name
        )

        if res:
            st.sidebar.success(
                f"Uploaded {res.get('record_count', 0)} records"
            )

up_c = st.sidebar.file_uploader(
    "Supplier C · JSON / Excel",
    type=["json", "xlsx", "xls", "csv"],
    key="up_c"
)

if up_c and st.sidebar.button(
    "Upload Supplier C",
    key="btn_up_c",
    use_container_width=True
):
    with st.spinner("Uploading Supplier C..."):
        res = APIClient.upload_file(
            "/api/uploads/supplier_c",
            up_c.getvalue(),
            up_c.name
        )

        if res:
            st.sidebar.success(
                f"Uploaded {res.get('record_count', 0)} records"
            )

st.sidebar.divider()

# Run pipeline
st.sidebar.markdown("#### 🚀 Pipeline Execution")

if st.sidebar.button(
    "Run Full Integration Pipeline",
    type="primary",
    use_container_width=True
):
    with st.spinner("Processing supplier feeds..."):
        run_res = APIClient.post("/api/uploads/pipeline/run")

        if run_res:
            st.sidebar.success(
                f"Pipeline completed: {run_res.get('status', 'Unknown')}"
            )
            st.rerun()
        else:
            st.sidebar.error("Pipeline execution failed. Check backend logs.")

st.sidebar.markdown("""
<div style="
    margin-top:25px;
    padding:12px;
    border-radius:10px;
    background:rgba(255,255,255,0.07);
    color:#bdcce3;
    font-size:10px;
    line-height:1.7;
">
    <b>PLATFORM ARCHITECTURE</b><br>
    Streamlit · FastAPI · PostgreSQL<br>
    <span style="color:#86efac;">●</span> Local workspace
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HERO SECTION
# --------------------------------------------------

st.markdown("""
<div class="hero">
    <h1>Supplier Product Data Integration Hub</h1>
    <p>
        Unify supplier feeds. Standardize product data.
        Resolve conflicts. Maintain complete data traceability.
    </p>
    <div class="hero-tag">
        ENTERPRISE DATA ENGINEERING WORKSPACE
    </div>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# BACKEND DATA
# --------------------------------------------------

stats = APIClient.get("/api/products/summary/stats") or {}
recon = APIClient.get("/api/metrics/reconciliation") or {}

supplier_stats = (
    APIClient.get("/api/metrics/suppliers/stats") or []
)

latest_runs = (
    APIClient.get("/api/metrics/runs?limit=1") or []
)

latest_run = latest_runs[0] if latest_runs else None


# --------------------------------------------------
# KPI METRICS
# --------------------------------------------------

section_heading(
    "Platform Overview",
    "Real-time summary of your supplier integration pipeline."
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    metric_card(
        "📦",
        "CANONICAL PRODUCTS",
        f"{stats.get('total_products', 0):,}"
    )

with col2:
    metric_card(
        "🏷️",
        "TOTAL BRANDS",
        f"{stats.get('total_brands', 0):,}"
    )

with col3:
    metric_card(
        "📥",
        "LAST RUN · INPUT",
        f"{latest_run.get('total_input_rows', 0):,}" if latest_run else "0"
    )

with col4:
    metric_card(
        "⚠️",
        "LAST RUN · REJECTED",
        f"{latest_run.get('rejected_rows', 0):,}" if latest_run else "0"
    )

with col5:
    latency = (
        f"{latest_run['run_duration_sec']:.3f}s"
        if latest_run and latest_run.get("run_duration_sec") is not None
        else "N/A"
    )

    metric_card(
        "⚡",
        "LAST RUN LATENCY",
        latency
    )


# --------------------------------------------------
# RECONCILIATION AUDIT
# --------------------------------------------------

section_heading(
    "Data Quality & Reconciliation",
    "Check whether incoming records are accounted for by the pipeline."
)

if recon and recon.get("reconciled"):
    st.markdown(
        f"""
        <div class="audit-ok">
            ✓ RECONCILIATION PASSED<br>
            <span style="font-weight:400;">
                {recon.get('reconciliation_formula', '')}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

elif recon and not recon.get("reconciled") and recon.get("status") != "NO_RUNS":
    st.markdown(
        """
        <div class="audit-error">
            ✕ RECONCILIATION DISCREPANCY DETECTED<br>
            <span style="font-weight:400;">
                Please inspect pipeline records and rejected data.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    st.info("Run the integration pipeline to generate reconciliation results.")


# --------------------------------------------------
# WORKSPACE NAVIGATION
# --------------------------------------------------

section_heading(
    "Integration Workspace",
    "Explore the different stages of your data integration platform."
)

w1, w2, w3, w4 = st.columns(4)

with w1:
    workspace_card(
        "📦",
        "Product Catalog",
        "Explore standardized products and your canonical product records."
    )

with w2:
    workspace_card(
        "🔍",
        "Lineage Explorer",
        "Trace product attributes back to their original supplier sources."
    )

with w3:
    workspace_card(
        "🛡️",
        "Quarantine Store",
        "Inspect invalid records and understand data quality failures."
    )

with w4:
    workspace_card(
        "📊",
        "Run Observability",
        "Monitor pipeline executions, processing counts and performance."
    )


# --------------------------------------------------
# SUPPLIER STATISTICS
# --------------------------------------------------

section_heading(
    "Supplier Intelligence",
    "Overview of the incoming data received from each supplier."
)

if supplier_stats:

    supp_df = pd.DataFrame(supplier_stats)

    supp_df = supp_df.rename(columns={
        "supplier_id": "Supplier Code",
        "name": "Supplier Organization",
        "priority": "Resolution Priority",
        "default_format": "Native Format",
        "total_raw_records": "Raw Records Ingested"
    })

    st.dataframe(
        supp_df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "No supplier records are available yet. Upload your sample feeds "
        "and execute the integration pipeline."
    )


# --------------------------------------------------
# LATEST PIPELINE EXECUTION
# --------------------------------------------------

section_heading(
    "Latest Pipeline Execution",
    "Details of the most recently recorded pipeline run."
)

if latest_run:

    run_col1, run_col2, run_col3 = st.columns(3)

    with run_col1:
        st.metric(
            "Run Status",
            str(latest_run.get("status", "Unknown")).upper()
        )

    with run_col2:
        st.metric(
            "Input Records",
            latest_run.get("total_input_rows", 0)
        )

    with run_col3:
        st.metric(
            "Rejected Records",
            latest_run.get("rejected_rows", 0)
        )

else:
    st.info("No pipeline executions have been recorded yet.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.markdown("""
<div style="
    text-align:center;
    padding:10px;
    color:#94a3b8;
    font-size:11px;
">
    Supplier Product Data Integration Hub
    &nbsp;·&nbsp; Streamlit + FastAPI + PostgreSQL
    <br>
    Data Engineering Workspace
</div>
""", unsafe_allow_html=True)
