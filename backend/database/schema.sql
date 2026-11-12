-- ==============================================================================
-- Supplier Product Data Integration Hub - PostgreSQL Schema
-- ==============================================================================

-- 1. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    priority INTEGER NOT NULL,
    default_format VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Source Files Table (Tracks uploaded or ingested feed files)
CREATE TABLE IF NOT EXISTS source_files (
    file_id VARCHAR(64) PRIMARY KEY,
    supplier_id VARCHAR(50) NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_format VARCHAR(20) NOT NULL,
    file_size_bytes BIGINT,
    record_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Pipeline Runs Table (Observability & execution audit metrics)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    total_input_rows INTEGER DEFAULT 0,
    valid_rows INTEGER DEFAULT 0,
    rejected_rows INTEGER DEFAULT 0,
    canonical_products_count INTEGER DEFAULT 0,
    run_duration_sec DOUBLE PRECISION DEFAULT 0.0,
    reconciliation_passed BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

-- 4. Raw Supplier Records (Preserving untouched source payloads for idempotency & audit)
CREATE TABLE IF NOT EXISTS raw_supplier_records (
    record_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    supplier_id VARCHAR(50) NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    file_id VARCHAR(64) REFERENCES source_files(file_id) ON DELETE SET NULL,
    source_record_id VARCHAR(255),
    record_fingerprint VARCHAR(64) NOT NULL,
    raw_payload JSON NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_supplier_record_fingerprint UNIQUE (supplier_id, record_fingerprint)
);

-- 5. Canonical Products (The golden standardized catalog)
CREATE TABLE IF NOT EXISTS canonical_products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(500) NOT NULL,
    brand VARCHAR(255) NOT NULL,
    manufacturer_part_number VARCHAR(255) NOT NULL,
    gtin VARCHAR(14),
    category VARCHAR(255),
    description TEXT,
    price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    stock_quantity INTEGER DEFAULT 0,
    supplier_id VARCHAR(50) REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    source_suppliers VARCHAR(255),
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Product Identifiers (Index of alternative codes like SKU, UPC, EAN for fast cross-referencing)
CREATE TABLE IF NOT EXISTS product_identifiers (
    id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(64) NOT NULL REFERENCES canonical_products(product_id) ON DELETE CASCADE,
    id_type VARCHAR(50) NOT NULL,  -- 'GTIN', 'MPN', 'SKU', 'BARCODE'
    id_value VARCHAR(255) NOT NULL,
    supplier_id VARCHAR(50) REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_identifier UNIQUE (product_id, id_type, id_value)
);

-- 7. Attribute-Level Lineage (Full audit trail of winning attributes)
CREATE TABLE IF NOT EXISTS attribute_lineage (
    lineage_id VARCHAR(64) PRIMARY KEY,
    product_id VARCHAR(64) NOT NULL REFERENCES canonical_products(product_id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    selected_value TEXT NOT NULL,
    original_source_value TEXT,
    supplier_name VARCHAR(255) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    source_record_id VARCHAR(255),
    source_timestamp TIMESTAMP WITH TIME ZONE,
    run_id VARCHAR(64) NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    selection_reason VARCHAR(255) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Quarantined Records (Bad records quarantined with rejection reasons)
CREATE TABLE IF NOT EXISTS quarantined_records (
    quarantine_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    supplier_id VARCHAR(50) NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    source_file VARCHAR(255) NOT NULL,
    raw_payload JSON NOT NULL,
    rejection_reason VARCHAR(500) NOT NULL,
    quarantined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- Indexes for Performance & Analytical Lookups
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_canonical_gtin ON canonical_products(gtin);
CREATE INDEX IF NOT EXISTS idx_canonical_brand_mpn ON canonical_products(brand, manufacturer_part_number);
CREATE INDEX IF NOT EXISTS idx_canonical_name ON canonical_products(product_name);
CREATE INDEX IF NOT EXISTS idx_lineage_product_id ON attribute_lineage(product_id);
CREATE INDEX IF NOT EXISTS idx_raw_supplier_run ON raw_supplier_records(supplier_id, run_id);
CREATE INDEX IF NOT EXISTS idx_quarantine_run ON quarantined_records(run_id);
CREATE INDEX IF NOT EXISTS idx_identifiers_value ON product_identifiers(id_type, id_value);
