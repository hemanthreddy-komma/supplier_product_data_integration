# Data Dictionary — Supplier Product Data Integration Hub

This document defines the schema, data types, constraints, and descriptions for all tables stored in PostgreSQL.

---

## 1. `suppliers`
Tracks registered suppliers, their priority hierarchy, and default formats.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `supplier_id` | VARCHAR(50) | No | PK | Unique identifier (e.g., `supplier_a`) |
| `name` | VARCHAR(255) | No | - | Supplier organization name |
| `priority` | INTEGER | No | - | Conflict resolution priority (1 = highest) |
| `default_format`| VARCHAR(20) | No | - | Expected feed format (`json` or `csv`) |
| `created_at` | TIMESTAMP | No | - | Registration timestamp |

---

## 2. `source_files`
Audit registry of uploaded or ingested supplier feed files.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `file_id` | VARCHAR(64) | No | PK | Unique file identifier (UUID) |
| `supplier_id` | VARCHAR(50) | No | FK $\rightarrow$ `suppliers` | Supplier that supplied the file |
| `file_name` | VARCHAR(255) | No | - | Original uploaded filename |
| `file_format` | VARCHAR(20) | No | - | `json` or `csv` |
| `file_size_bytes`| BIGINT | Yes | - | Size in bytes |
| `record_count` | INTEGER | No | - | Total rows parsed from file |
| `uploaded_at` | TIMESTAMP | No | - | Upload timestamp |

---

## 3. `pipeline_runs`
Observability table tracking operational execution metrics and reconciliation checks.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `run_id` | VARCHAR(64) | No | PK | Execution run identifier |
| `started_at` | TIMESTAMP | No | - | Pipeline execution start timestamp |
| `completed_at` | TIMESTAMP | Yes | - | Execution completion timestamp |
| `status` | VARCHAR(50) | No | - | `SUCCESS`, `FAILED`, `COMPLETED_EMPTY` |
| `total_input_rows`| INTEGER | No | - | Total raw records ingested |
| `valid_rows` | INTEGER | No | - | Total records passing data quality |
| `rejected_rows` | INTEGER | No | - | Total quarantined records |
| `canonical_products_count`| INTEGER | No | - | Distinct golden products produced |
| `run_duration_sec`| DOUBLE | No | - | Wall-clock execution time in seconds |
| `reconciliation_passed`| BOOLEAN | No | - | True if `total_input == valid + rejected` |
| `error_message` | TEXT | Yes | - | Error stack trace if failed |

---

## 4. `raw_supplier_records`
Preserves untouched source payloads for idempotency, debugging, and auditing.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `record_id` | VARCHAR(64) | No | PK | Unique raw record UUID |
| `run_id` | VARCHAR(64) | No | FK $\rightarrow$ `pipeline_runs` | Associated run |
| `supplier_id` | VARCHAR(50) | No | FK $\rightarrow$ `suppliers` | Contributing supplier |
| `source_record_id`| VARCHAR(255)| Yes | - | Supplier's internal SKU or part number |
| `record_fingerprint`| VARCHAR(64)| No | UNIQUE(supplier, fp) | SHA-256 payload hash |
| `raw_payload` | JSON | No | - | Untouched source JSON/dict payload |
| `ingested_at` | TIMESTAMP | No | - | Ingestion timestamp |

---

## 5. `canonical_products`
The standardized golden product catalog.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `product_id` | VARCHAR(64) | No | PK | Deterministic UUIDv5 |
| `product_name` | VARCHAR(500) | No | - | Standardized title |
| `brand` | VARCHAR(255) | No | - | Normalized brand name |
| `manufacturer_part_number`| VARCHAR(255)| No | - | Normalized MPN / model number |
| `gtin` | VARCHAR(14) | Yes | INDEX | 14-digit GS1 barcode code |
| `category` | VARCHAR(255) | Yes | - | Unified taxonomy category |
| `description` | TEXT | Yes | - | Product description |
| `price` | DOUBLE | No | - | Winning price in USD |
| `currency` | VARCHAR(10) | No | Default 'USD' | Currency code |
| `stock_quantity`| INTEGER | No | - | Available stock count |
| `supplier_id` | VARCHAR(50) | Yes | FK $\rightarrow$ `suppliers` | Primary winning supplier |
| `source_suppliers`| VARCHAR(255)| Yes | - | Comma-separated contributing suppliers |
| `status` | VARCHAR(50) | No | Default 'ACTIVE' | Status (`ACTIVE`, `INCOMPLETE`) |
| `created_at` | TIMESTAMP | No | - | Initial creation timestamp |
| `updated_at` | TIMESTAMP | No | - | Last update timestamp |

---

## 6. `product_identifiers`
Alternative identifier cross-reference table.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `id` | VARCHAR(64) | No | PK | Deterministic UUIDv5 |
| `product_id` | VARCHAR(64) | No | FK $\rightarrow$ `canonical_products` | Linked golden product |
| `id_type` | VARCHAR(50) | No | - | `GTIN`, `MPN`, `SKU`, `UPC`, `EAN` |
| `id_value` | VARCHAR(255) | No | UNIQUE(prod, type, val) | Standardized code string |
| `supplier_id` | VARCHAR(50) | Yes | FK $\rightarrow$ `suppliers` | Supplier contributing code |
| `created_at` | TIMESTAMP | No | - | Registration timestamp |

---

## 7. `attribute_lineage`
Full attribute-level audit trail.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `lineage_id` | VARCHAR(64) | No | PK | Unique lineage record UUID |
| `product_id` | VARCHAR(64) | No | FK $\rightarrow$ `canonical_products` | Linked golden product |
| `attribute_name`| VARCHAR(100)| No | - | `price`, `product_name`, `stock`, etc. |
| `selected_value`| TEXT | No | - | Final winning attribute value |
| `original_source_value`| TEXT | Yes | - | Untouched source attribute string |
| `supplier_name`| VARCHAR(255)| No | - | Winning supplier organization |
| `source_file` | VARCHAR(255) | No | - | Source filename |
| `source_record_id`| VARCHAR(255)| Yes | - | Source SKU or part number |
| `source_timestamp`| TIMESTAMP | Yes | - | Source observation timestamp |
| `run_id` | VARCHAR(64) | No | FK $\rightarrow$ `pipeline_runs` | Pipeline run ID |
| `selection_reason`| VARCHAR(255)| No | - | Priority rule or fallback rationale |
| `recorded_at` | TIMESTAMP | No | - | Recording timestamp |

---

## 8. `quarantined_records`
Isolated invalid records with diagnostic error reasons.

| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `quarantine_id`| VARCHAR(64) | No | PK | Unique quarantine record UUID |
| `run_id` | VARCHAR(64) | No | FK $\rightarrow$ `pipeline_runs` | Pipeline run ID |
| `supplier_id` | VARCHAR(50) | No | FK $\rightarrow$ `suppliers` | Supplier submitting row |
| `source_file` | VARCHAR(255) | No | - | Source filename |
| `raw_payload` | JSON | No | - | Original payload |
| `rejection_reason`| VARCHAR(500)| No | - | Diagnostic reason for quarantine |
| `quarantined_at`| TIMESTAMP | No | - | Quarantine timestamp |
