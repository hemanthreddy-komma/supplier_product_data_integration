# 📦 Supplier Product Data Integration Hub

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%20%7C%2016%20%7C%2018-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg)](https://www.sqlalchemy.org/)
[![Pytest](https://img.shields.io/badge/Pytest-21%20Passed-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A decoupled, three-tier data engineering platform that unifies heterogeneous supplier product feeds (**CSV, JSON, and Excel**) into an authoritative **Canonical Product Catalog (Golden Record)** with strict schema validation, two-tier entity resolution, priority conflict handling, field-level provenance lineage, and observability.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TIER 1: PRESENTATION                            │
│  Streamlit Multi-Page UI (Catalog, Lineage, Quarantine, Metrics)       │
│  * Strict zero-ETL design: communicates exclusively via HTTP REST API  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON (Port: 8000)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        TIER 2: APPLICATION                             │
│  FastAPI REST API & Modular ETL Services (backend/services/)           │
│                                                                        │
│  [Ingestion] ──> [Standardization] ──> [Validation & GS1 Checksum]    │
│                                                   │                    │
│  [Persistence] <── [Lineage] <── [Conflicts] <── [Entity Resolution]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy 2.0 / SQL (Port: 5432)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        TIER 3: DATA PERSISTENCE                        │
│  PostgreSQL Database: supplier_product_db (8 Normalized Tables)        │
│  * Automatic offline failover to local SQLite (local_catalog.db)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Pipeline Highlights

1. **Multi-Format Ingestion & Idempotency**:
   - Ingests CSV, JSON, and Microsoft Excel (`.xlsx` / `.xls`) feeds.
   - Computes deterministic SHA-256 payload fingerprints stored under a `UNIQUE(supplier_id, record_fingerprint)` constraint to guarantee safe, idempotent re-runs.

2. **Validation & GS1 Modulo-10 Checksum**:
   - Enforces positive pricing (`price > 0`), non-negative stock (`stock >= 0`), and non-empty titles.
   - Computes official GS1 Modulo-10 check-digits for GTIN-8, GTIN-12 (UPC), GTIN-13 (EAN), and GTIN-14:
     $$\text{Total} = \sum_{i=1}^{N-1} d_i \times w_i \quad (w \in \{3, 1, 3, 1, \dots\}), \quad C_{\text{calc}} = (10 - (\text{Total} \pmod{10})) \pmod{10}$$
   - Corrupted or invalid records are isolated in `quarantined_records` with raw payloads and diagnostic error codes.

3. **Two-Tier Entity Resolution**:
   - **Tier 1 (GTIN Match)**: Primary clustering via standardized 14-digit GTIN barcodes.
   - **Tier 2 (Brand + MPN Fallback)**: Resolves records missing barcodes via normalized `(brand.lower() + "::" + mpn.lower())`.
   - **Ambiguity Guard**: Unmatched or ambiguous records remain isolated to guarantee zero false merges.
   - **Deterministic UUIDv5**: Generated via `uuid.uuid5(NAMESPACE_OID, cluster_key)`.

4. **Conflict Resolution & Field Lineage**:
   - Configurable supplier priority hierarchy:
     $$\text{Supplier A (Priority 1: High Trust)} > \text{Supplier B (Priority 2)} > \text{Supplier C (Priority 3)}$$
   - Newest observation timestamp breaks priority ties.
   - If a high-priority supplier provides a `null` attribute, the engine falls back down the priority chain.
   - Every attribute value records its winning supplier, source file, SKU, and rule in `attribute_lineage`.

5. **Observability & Mathematical Reconciliation**:
   - Every run verifies the invariant:
     $$N_{\text{total\_input}} = N_{\text{valid}} + N_{\text{quarantined}}$$
   - Telemetry tracks run duration, supplier row counts, and rejection breakdowns.

---

## 🗄️ Database Schema (8 Tables)

| Table | Purpose | Key Constraints |
|---|---|---|
| `suppliers` | Registered supplier priority configuration | Primary Key: `supplier_id`, priority 1-3 |
| `source_files` | Ingestion audit log of uploaded feed files | Primary Key: `file_id`, Foreign Key $\rightarrow$ `suppliers` |
| `pipeline_runs` | Execution telemetry & reconciliation logs | Primary Key: `run_id`, status, duration, row counts |
| `raw_supplier_records` | Immutable source payloads for idempotency | Compound Unique: `(supplier_id, record_fingerprint)` |
| `canonical_products` | Standardized Golden Product Catalog | Primary Key: `product_id` (UUIDv5), winning price & stock |
| `product_identifiers` | Cross-reference index for GTIN, MPN, SKU | Unique: `(product_id, id_type, id_value)` |
| `attribute_lineage` | Field-level provenance and audit trail | Primary Key: `lineage_id`, tracks supplier, rule, and file |
| `quarantined_records` | Isolated bad data with error reasons | Primary Key: `quarantine_id`, stores raw JSON & diagnostics |

---

## 🚀 Quickstart Guide

### 1. Setup Environment & Install Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Database
Copy `.env.example` to `.env` and configure your PostgreSQL connection:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:your_password@127.0.0.1:5432/supplier_product_db
```
*(Note: If PostgreSQL is offline, the engine automatically fails over to local SQLite `local_catalog.db` with zero downtime).*

### 3. Run Automated Tests
```powershell
python -m pytest -v
```
👉 Expected: **21 passed in < 2 seconds** across ingestion, validation, resolution, conflicts, and pipeline.

### 4. Run Performance Benchmark
```powershell
python benchmark.py
```
👉 Expected: **~3,250 records/sec** throughput with <47 MB RAM on 25,000 records.

### 5. Launch Application
Open two terminal windows:

* **Terminal 1 — FastAPI Backend Engine:**
  ```powershell
  uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
  ```
  Swagger Docs: `http://127.0.0.1:8000/docs`

* **Terminal 2 — Streamlit Frontend Dashboard:**
  ```powershell
  streamlit run frontend/app.py
  ```
  Dashboard UI: `http://localhost:8501`

---

## 🎤 Live Demonstration & SQL Verification Guide

### Step 1: Execute Pipeline via CLI or UI
```powershell
python run_pipeline.py
```

### Step 2: Verify Results in Database (`check_db.py` or `psql`)
```powershell
python check_db.py
```

Or query PostgreSQL directly via `psql`:
```sql
-- 1. View total golden products created
SELECT count(*) FROM canonical_products;

-- 2. Inspect golden products and winning prices
SELECT product_name, brand, price, stock_quantity, source_suppliers 
FROM canonical_products 
ORDER BY price DESC 
LIMIT 5;

-- 3. Inspect field-level lineage (proves auditability)
SELECT attribute_name, selected_value, supplier_name, selection_reason 
FROM attribute_lineage 
LIMIT 5;

-- 4. Inspect quarantined bad records and diagnostic reasons
SELECT supplier_id, rejection_reason, source_file 
FROM quarantined_records;

-- 5. Inspect mathematical reconciliation assertion
SELECT run_id, total_input_rows, valid_rows, rejected_rows, reconciliation_passed 
FROM pipeline_runs 
ORDER BY started_at DESC 
LIMIT 1;
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check & active database engine |
| `POST` | `/api/uploads/{supplier_id}` | Upload and stage supplier feed (`.csv`, `.json`, `.xlsx`) |
| `POST` | `/api/uploads/pipeline/run` | Trigger the integration pipeline |
| `GET` | `/api/products` | Query canonical products (search, brand, category, pagination) |
| `GET` | `/api/products/export/csv` | Download canonical catalog as CSV |
| `GET` | `/api/products/export/excel` | Download canonical catalog as formatted Excel (`.xlsx`) |
| `GET` | `/api/lineage/product/{id}` | Retrieve field-level provenance audit trail for a product |
| `GET` | `/api/metrics/quarantine` | Query quarantined invalid records |
| `POST` | `/api/metrics/quarantine/{id}/reprocess` | **Remediation**: Fix faulty payload and re-inject into catalog |
| `GET` | `/api/metrics/reconciliation` | Verify mathematical reconciliation invariant ($N_{in} = N_{val} + N_{rej}$) |

---

## 📁 Repository Structure

```text
supplier_product_integration/
├── frontend/                  # Tier 1: Presentation Layer (Streamlit)
│   ├── app.py                 # Pipeline Console & Upload Controls
│   ├── pages/                 # Multi-page views (Catalog, Lineage, Quarantine, Metrics)
│   └── components/api_client.py # Decoupled REST API Client
├── backend/                   # Tier 2: Application Layer (FastAPI)
│   ├── main.py                # FastAPI Application Entry & CORS
│   ├── api/routes/            # REST Endpoints (uploads, products, lineage, metrics)
│   ├── services/              # Domain ETL services (ingest, validate, resolve, conflicts)
│   ├── models/schemas.py      # Pydantic v2 Contracts
│   └── database/              # Tier 3: Persistence (PostgreSQL schema.sql, models.py, connection.py)
├── data/
│   ├── raw/                   # Active feeds (supplier_a.json, supplier_b.csv, supplier_c.json)
│   └── demo_feeds/            # 68 real-world commercial test feeds (Apple, Sony, Dell, etc.)
├── tests/                     # 21 Automated Pytest Unit & Integration Tests
├── docs/                      # Technical specifications & rubric defense
│   ├── design_choices_and_limitations.md # Rubric mapping & candidate defense
│   ├── data_dictionary.md     # 8-table database schema dictionary
│   └── architecture.md        # System design specifications
├── benchmark.py               # Performance reasoning & profiling tool
├── run_pipeline.py            # Standalone CLI pipeline executor
├── check_db.py                # Database verification inspector
└── requirements.txt           # Python dependencies
```

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
