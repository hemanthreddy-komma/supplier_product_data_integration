"""
Root Pipeline Runner Script
Executes the full supplier integration pipeline and persists canonical records,
quarantined records, product identifiers, and attribute lineage directly into PostgreSQL.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.database.connection import engine, init_db
from backend.services.pipeline import PipelineService


def main():
    print("\n" + "=" * 70)
    print("      SUPPLIER PRODUCT DATA INTEGRATION - PIPELINE EXECUTION")
    print("=" * 70)
    print(f"Connecting to database: {engine.url}")

    # Ensure schema and suppliers are initialized
    init_db()

    # Execute pipeline
    orchestrator = PipelineService()
    summary = orchestrator.execute_pipeline()

    print("\n" + "=" * 70)
    print(f"PIPELINE RUN FINISHED: {summary['status']}")
    print(f"  Run ID:                  {summary['run_id']}")
    print(f"  Duration:                {summary['run_duration_sec']:.3f} seconds")
    print(f"  Total Ingested Records:  {summary['total_input_rows']}")
    print(f"  Valid Records:           {summary['valid_rows']}")
    print(f"  Quarantined Bad Records: {summary['rejected_rows']}")
    print(f"  Canonical Products:      {summary['canonical_products_count']}")
    print(f"  Reconciliation Check:    {'PASSED (100%)' if summary['reconciliation_passed'] else 'FAILED'}")
    print("=" * 70 + "\n")
    print("You can now query PostgreSQL via psql to view the stored data!")


if __name__ == "__main__":
    main()
