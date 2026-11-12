import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.api.dependencies import get_db
from backend.database.models import (
    AttributeLineage,
    CanonicalProduct,
    PipelineRun,
    ProductIdentifier,
    QuarantinedRecord,
    RawSupplierRecord,
    Supplier,
)
from backend.models.schemas import PipelineRunSummary, QuarantinedRecordOut
from backend.services.conflict_resolution import ConflictResolutionService
from backend.services.ingestion import compute_payload_fingerprint
from backend.services.resolution import EntityResolutionService
from backend.services.standardization import StandardizationService
from backend.services.validation import ValidationService

router = APIRouter(prefix="/api/metrics", tags=["Observability & Metrics"])


@router.get("/runs", response_model=List[PipelineRunSummary])
def get_pipeline_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve historical pipeline runs and execution metrics."""
    return db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit).all()


@router.get("/quarantine", response_model=List[QuarantinedRecordOut])
def get_quarantined_records(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Retrieve quarantined records with error reasons and payloads."""
    return db.query(QuarantinedRecord).order_by(QuarantinedRecord.quarantined_at.desc()).limit(limit).all()


@router.get("/quarantine/reasons")
def get_rejection_reasons_summary(db: Session = Depends(get_db)):
    """Counts grouped by rejection reason."""
    reasons = (
        db.query(QuarantinedRecord.rejection_reason, func.count(QuarantinedRecord.quarantine_id))
        .group_by(QuarantinedRecord.rejection_reason)
        .all()
    )
    return [{"reason": r[0], "count": r[1]} for r in reasons]


@router.get("/reconciliation")
def get_reconciliation_status(db: Session = Depends(get_db)):
    """Validates source-to-target reconciliation assertion for the latest run."""
    latest_run = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    if not latest_run:
        return {"status": "NO_RUNS", "reconciled": False}

    reconciled = latest_run.total_input_rows == (latest_run.valid_rows + latest_run.rejected_rows)
    return {
        "run_id": latest_run.run_id,
        "started_at": latest_run.started_at,
        "total_input_rows": latest_run.total_input_rows,
        "valid_rows": latest_run.valid_rows,
        "rejected_rows": latest_run.rejected_rows,
        "canonical_products_count": latest_run.canonical_products_count,
        "reconciled": reconciled,
        "reconciliation_formula": f"{latest_run.total_input_rows} (Input) == {latest_run.valid_rows} (Valid) + {latest_run.rejected_rows} (Quarantined)"
    }


@router.get("/suppliers/stats")
def get_supplier_statistics(db: Session = Depends(get_db)):
    """Aggregates ingestion counts per supplier."""
    counts = (
        db.query(RawSupplierRecord.supplier_id, func.count(RawSupplierRecord.record_id))
        .group_by(RawSupplierRecord.supplier_id)
        .all()
    )
    supplier_map = {c[0]: c[1] for c in counts}
    suppliers = db.query(Supplier).all()
    
    result = []
    for s in suppliers:
        result.append({
            "supplier_id": s.supplier_id,
            "name": s.name,
            "priority": s.priority,
            "default_format": s.default_format,
            "total_raw_records": supplier_map.get(s.supplier_id, 0)
        })
    return result


@router.post("/quarantine/{quarantine_id}/reprocess")
def reprocess_quarantined_record(
    quarantine_id: str,
    corrected_payload: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Remediation Workflow: Allows an operator to submit corrected fields for a quarantined record,
    re-validates it, standardizes it, resolves it, and integrates it into the canonical catalog.
    """
    q_rec = db.query(QuarantinedRecord).filter(QuarantinedRecord.quarantine_id == quarantine_id).first()
    if not q_rec:
        raise HTTPException(status_code=404, detail="Quarantined record not found")

    payload = corrected_payload if corrected_payload is not None else q_rec.raw_payload
    fingerprint = compute_payload_fingerprint(payload)

    raw_entry = {
        "record_id": str(uuid.uuid4()),
        "supplier_id": q_rec.supplier_id,
        "file_name": q_rec.source_file,
        "source_record_id": str(payload.get("sku") or payload.get("part_number") or payload.get("sku_id") or ""),
        "record_fingerprint": fingerprint,
        "raw_payload": payload
    }

    # Standardize
    std_rec = StandardizationService.standardize(raw_entry)

    # Validate
    is_valid, rejection_reason = ValidationService.validate_record(std_rec)
    if not is_valid:
        return {
            "success": False,
            "message": f"Remediation failed validation: {rejection_reason}",
            "quarantine_id": quarantine_id
        }

    # Resolve cluster
    clusters = EntityResolutionService.resolve_clusters([std_rec])
    for prod_id, cluster_records in clusters.items():
        resolved_dict, lineage_decisions = ConflictResolutionService.resolve_cluster_attributes(prod_id, cluster_records)

        # Check existing product
        existing_prod = db.query(CanonicalProduct).filter(CanonicalProduct.product_id == prod_id).first()
        if existing_prod:
            for k, v in resolved_dict.items():
                if k != "product_id" and v is not None:
                    setattr(existing_prod, k, v)
        else:
            new_prod = CanonicalProduct(**resolved_dict)
            db.add(new_prod)

        # Record lineage
        for lin in lineage_decisions:
            db_lin = AttributeLineage(
                lineage_id=str(uuid.uuid4()),
                product_id=prod_id,
                attribute_name=lin["attribute_name"],
                selected_value=str(lin["selected_value"]),
                original_source_value=str(lin.get("original_source_value") or ""),
                supplier_name=lin["supplier_name"],
                source_file=lin["source_file"],
                source_record_id=lin.get("source_record_id"),
                source_timestamp=lin.get("source_timestamp"),
                run_id=q_rec.run_id,
                selection_reason=f"REMEDIATION: {lin['selection_reason']}"
            )
            db.add(db_lin)

        # Identifiers
        if std_rec.gtin:
            db.add(ProductIdentifier(
                id=str(uuid.uuid4()),
                product_id=prod_id,
                id_type="GTIN",
                id_value=std_rec.gtin,
                supplier_id=q_rec.supplier_id
            ))

    # Remove from quarantine store
    db.delete(q_rec)
    db.commit()

    return {
        "success": True,
        "message": "Record successfully remediated, validated, and promoted to canonical catalog!",
        "quarantine_id": quarantine_id,
        "product_id": prod_id
    }
