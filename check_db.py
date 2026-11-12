

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.database.connection import engine, execute_raw_sql


def inspect_database():
    print("\n" + "=" * 75)
    print("           DATABASE PERSISTENCE INSPECTOR")
    print("=" * 75)
    print(f"Configured Database URL: {settings.DATABASE_URL}")
    print(f"Active Engine Dialect:   {engine.name.upper()} ({engine.url})")
    print("=" * 75)

    tables = [
        "suppliers",
        "source_files",
        "raw_supplier_records",
        "canonical_products",
        "product_identifiers",
        "attribute_lineage",
        "quarantined_records",
        "pipeline_runs"
    ]

    print("\n[1] TABLE ROW COUNTS IN DATABASE:")
    print("-" * 50)
    with engine.connect() as conn:
        for tbl in tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                print(f"  * {tbl.ljust(25)} : {count} rows")
            except Exception as e:
                print(f"  * {tbl.ljust(25)} : Table not found or error ({e})")

    # [2] Canonical Products Sample
    print("\n[2] CANONICAL PRODUCTS (GOLDEN CATALOG):")
    print("-" * 75)
    with engine.connect() as conn:
        query = text("""
            SELECT product_id, product_name, brand, manufacturer_part_number, price, stock_quantity, source_suppliers
            FROM canonical_products
            ORDER BY updated_at DESC
            LIMIT 5;
        """)
        prods = conn.execute(query).fetchall()
        if prods:
            df = pd.DataFrame(prods)
            print(df.to_string(index=False))
        else:
            print("  (No canonical products found. Run the pipeline first!)")

    # [3] Attribute Lineage Sample
    print("\n[3] ATTRIBUTE LINEAGE (FIELD-LEVEL AUDIT TRAIL):")
    print("-" * 75)
    with engine.connect() as conn:
        query = text("""
            SELECT attribute_name, selected_value, supplier_name, selection_reason, source_file
            FROM attribute_lineage
            ORDER BY recorded_at DESC
            LIMIT 5;
        """)
        lineage = conn.execute(query).fetchall()
        if lineage:
            df = pd.DataFrame(lineage)
            print(df.to_string(index=False))
        else:
            print("  (No lineage records found.)")

    # [4] Quarantined Records Sample
    print("\n[4] QUARANTINED RECORDS (ISOLATED BAD DATA):")
    print("-" * 75)
    with engine.connect() as conn:
        query = text("""
            SELECT quarantine_id, supplier_id, rejection_reason, source_file
            FROM quarantined_records
            ORDER BY quarantined_at DESC
            LIMIT 5;
        """)
        rejects = conn.execute(query).fetchall()
        if rejects:
            df = pd.DataFrame(rejects)
            print(df.to_string(index=False))
        else:
            print("  (No quarantined records found.)")

    # [5] Pipeline Execution Runs
    print("\n[5] PIPELINE EXECUTION AUDIT RUNS:")
    print("-" * 75)
    with engine.connect() as conn:
        query = text("""
            SELECT run_id, status, total_input_rows, valid_rows, rejected_rows, canonical_products_count, run_duration_sec, reconciliation_passed
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT 5;
        """)
        runs = conn.execute(query).fetchall()
        if runs:
            df = pd.DataFrame(runs)
            print(df.to_string(index=False))
        else:
            print("  (No pipeline execution history found.)")

    print("\n" + "=" * 75)
    print("                     INSPECTION COMPLETE")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    inspect_database()
