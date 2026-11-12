import pytest
from backend.database.models import (
    AttributeLineage,
    CanonicalProduct,
    PipelineRun,
    ProductIdentifier,
    QuarantinedRecord,
    RawSupplierRecord,
)
from backend.services.pipeline import PipelineService


def test_pipeline_execution_and_persistence(test_db):
    pipeline = PipelineService(db_session=test_db)
    summary = pipeline.execute_pipeline(custom_run_id="test_run_001")

    assert summary["status"] == "SUCCESS"
    assert summary["total_input_rows"] > 0
    assert summary["valid_rows"] > 0
    assert summary["rejected_rows"] > 0
    assert summary["canonical_products_count"] > 0

    # Reconciliation check
    assert summary["reconciliation_passed"] is True
    assert summary["total_input_rows"] == summary["valid_rows"] + summary["rejected_rows"]

    # Check database persistence
    canonical_count = test_db.query(CanonicalProduct).count()
    assert canonical_count == summary["canonical_products_count"]

    lineage_count = test_db.query(AttributeLineage).count()
    assert lineage_count > 0

    quarantine_count = test_db.query(QuarantinedRecord).count()
    assert quarantine_count == summary["rejected_rows"]

    identifiers_count = test_db.query(ProductIdentifier).count()
    assert identifiers_count > 0


def test_pipeline_idempotency(test_db):
    pipeline = PipelineService(db_session=test_db)

    # First run
    run1 = pipeline.execute_pipeline(custom_run_id="run_batch_1")
    count_1 = test_db.query(CanonicalProduct).count()
    ids_1 = set(row[0] for row in test_db.query(CanonicalProduct.product_id).all())

    # Second run with exact same data
    run2 = pipeline.execute_pipeline(custom_run_id="run_batch_2")
    count_2 = test_db.query(CanonicalProduct).count()
    ids_2 = set(row[0] for row in test_db.query(CanonicalProduct.product_id).all())

    # IDEMPOTENCY: Canonical product count and IDs must not duplicate!
    assert count_1 == count_2
    assert ids_1 == ids_2

    # Exactly 2 runs recorded in audit log
    runs_count = test_db.query(PipelineRun).count()
    assert runs_count == 2


def test_empty_batch_handling(test_db):
    pipeline = PipelineService(db_session=test_db)
    summary = pipeline.execute_pipeline(custom_files={}, custom_run_id="run_empty")

    assert summary["status"] == "COMPLETED_EMPTY"
    assert summary["total_input_rows"] == 0
    assert summary["canonical_products_count"] == 0
    assert summary["reconciliation_passed"] is True
