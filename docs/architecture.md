# Architecture Overview — Supplier Product Data Integration Hub

The **Supplier Product Data Integration Hub** is designed as an enterprise three-tier system that decouples Presentation, Application Business Logic, and Data Persistence.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TIER 1: PRESENTATION                            │
│  Streamlit Multi-Page Dashboard (frontend/app.py & pages/)             │
│  - 1_Product_Catalog: Search, filter, inspect, and export catalog     │
│  - 2_Lineage_Explorer: Field-level provenance & conflict audit trail   │
│  - 3_Quarantine: Quarantined records & payload inspector               │
│  - 4_Run_Metrics: Execution telemetry & reconciliation assertions      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (HTTP / JSON)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        TIER 2: APPLICATION                             │
│  FastAPI REST API & Core ETL Engine (backend/)                         │
│                                                                        │
│  ┌───────────────────────┐       ┌──────────────────────────────────┐  │
│  │ Ingestion Service     │──────>│ Standardization Service          │  │
│  │ (CSV & JSON feeds)    │       │ (Field normalizer & cleaner)     │  │
│  └───────────────────────┘       └─────────────────┬────────────────┘  │
│                                                    │                   │
│  ┌───────────────────────┐       ┌─────────────────▼────────────────┐  │
│  │ Entity Resolution     │<──────│ Validation Service               │  │
│  │ (GTIN -> Brand+MPN)   │       │ (GS1 Modulo-10, price/stock QA)  │  │
│  └───────────┬───────────┘       └──────────────────────────────────┘  │
│              │                                                         │
│  ┌───────────▼───────────┐       ┌──────────────────────────────────┐  │
│  │ Conflict Resolution   │──────>│ Lineage & Pipeline Orchestrator  │  │
│  │ (Supplier priorities) │       │ (Execution telemetry & metrics)  │  │
│  └───────────────────────┘       └─────────────────┬────────────────┘  │
└────────────────────────────────────────────────────┼───────────────────┘
                                                     │ SQLAlchemy ORM / SQL
┌────────────────────────────────────────────────────▼───────────────────┐
│                        TIER 3: DATA PERSISTENCE                        │
│  PostgreSQL Database (backend/database/)                               │
│  - suppliers: Configurable supplier priorities                         │
│  - source_files: Metadata of uploaded feed files                       │
│  - raw_supplier_records: Untouched source payloads with fingerprints   │
│  - canonical_products: Golden standardized catalog                     │
│  - product_identifiers: Lookup index for GTIN, MPN, SKU               │
│  - attribute_lineage: Field-level provenance and resolution rules      │
│  - quarantined_records: Quarantined rows with rejection diagnostics    │
│  - pipeline_runs: Observability & audit run telemetry                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Core Pipeline Workflows

### 1. Ingestion & Fingerprinting
Feeds are ingested from CSV and JSON files. For every incoming raw record, a deterministic SHA-256 fingerprint is calculated based on its payload. This allows repeated ingestions of the same file to be completely idempotent: existing raw records are recognized and not duplicated.

### 2. Standardization
Supplier-specific field names (e.g. `product_title` vs `product_description` vs `name`) are standardized into canonical fields:
- `product_name`, `brand`, `manufacturer_part_number`, `gtin`, `category`, `description`, `price`, `currency`, `stock_quantity`.
Brand names and part numbers are trimmed and normalized.

### 3. Validation & Quarantine
Incoming records pass through strict validation:
1. Non-empty product name.
2. Positive price (`price > 0`).
3. Non-negative stock (`stock >= 0`).
4. GS1 Modulo-10 checksum validation on GTIN barcodes.
5. Presence of valid GTIN or normalized (Brand + MPN).
Records violating any of these rules are quarantined in `quarantined_records` with human-readable error reasons.

### 4. Two-Tier Entity Resolution
1. **Primary Match**: Standardized 14-digit GTIN / UPC / EAN with valid checksums.
2. **Fallback Match**: When GTIN is absent or unparseable, matching falls back to normalized `(brand.lower().strip(), mpn.lower().strip())`.
3. **Uncertain Matches**: Ambiguous records with conflicting attributes or missing identifiers are never merged automatically.

### 5. Conflict Resolution & Lineage
When multiple suppliers supply data for the same canonical product:
- Configurable priority is applied:
  - `supplier_a (Priority 1) > supplier_b (Priority 2) > supplier_c (Priority 3)`
- In case of identical priority, the newest observation timestamp breaks the tie.
- If a high-priority supplier lacks an attribute (e.g., description is `null`), the system falls back to lower-priority suppliers that provide a non-null value.
- Every winning value is recorded in `attribute_lineage` with the exact supplier, source file, timestamp, and resolution rule.
