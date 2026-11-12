from datetime import datetime, timezone
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import (
    AttributeLineage,
    CanonicalProduct,
    PipelineRun,
    ProductIdentifier,
    QuarantinedRecord,
    RawSupplierRecord,
)
from backend.services.conflict_resolution import ConflictResolutionService
from backend.services.ingestion import IngestionService
from backend.services.lineage import LineageService
from backend.services.resolution import EntityResolutionService
from backend.services.standardization import StandardizationService
from backend.services.validation import ValidationService

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineService:
    """
    Tier 2 Pipeline Orchestrator:
    Coordinates ingestion, standardization, validation, entity resolution,
    conflict resolution, and persistence into the PostgreSQL database.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self._db = db_session

    def execute_pipeline(
        self,
        custom_files: Optional[Dict[str, Path]] = None,
        custom_run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = _utc_now()
        t0 = time.time()
        run_id = custom_run_id or f"run_{start_time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        session = self._db or SessionLocal()
        close_session = self._db is None

        logger.info(f"=== Starting Supplier Product Data Integration Pipeline [{run_id}] ===")

        try:
            # 1. Determine Feed Files
            feed_files: Dict[str, Path] = {}
            if custom_files is not None:
                feed_files = custom_files
            else:
                for s_id in settings.SUPPLIER_PRIORITIES.keys():
                    # Discover active feed file across supported formats (.xlsx, .csv, .json)
                    found = False
                    for ext in [".xlsx", ".xls", ".csv", ".json"]:
                        p = settings.RAW_DATA_DIR / f"{s_id}{ext}"
                        if p.exists():
                            feed_files[s_id] = p
                            found = True
                            break

            if not feed_files:
                duration = round(time.time() - t0, 3)
                empty_run = PipelineRun(
                    run_id=run_id,
                    started_at=start_time,
                    completed_at=_utc_now(),
                    status="COMPLETED_EMPTY",
                    total_input_rows=0,
                    valid_rows=0,
                    rejected_rows=0,
                    canonical_products_count=0,
                    run_duration_sec=duration,
                    reconciliation_passed=True
                )
                session.add(empty_run)
                session.commit()
                return {
                    "run_id": run_id,
                    "status": "COMPLETED_EMPTY",
                    "total_input_rows": 0,
                    "valid_rows": 0,
                    "rejected_rows": 0,
                    "canonical_products_count": 0,
                    "run_duration_sec": duration,
                    "reconciliation_passed": True
                }

            # 2. INGESTION & IDEMPOTENT RAW RECORD STORE
            all_raw_entries = []
            for s_id, file_path in feed_files.items():
                entries, _ = IngestionService.parse_feed_file(file_path, s_id)
                all_raw_entries.extend(entries)

            # Persist raw records idempotently (ignore duplicates based on fingerprint)
            existing_fingerprints = set(
                row[0] for row in session.query(RawSupplierRecord.record_fingerprint).all()
            )
            for r in all_raw_entries:
                if r["record_fingerprint"] not in existing_fingerprints:
                    raw_model = RawSupplierRecord(
                        record_id=r["record_id"],
                        run_id=run_id,
                        supplier_id=r["supplier_id"],
                        source_record_id=r.get("source_record_id"),
                        record_fingerprint=r["record_fingerprint"],
                        raw_payload=r["raw_payload"],
                        ingested_at=start_time
                    )
                    session.add(raw_model)
                    existing_fingerprints.add(r["record_fingerprint"])

            # 3. STANDARDIZATION & 4. VALIDATION
            valid_records = []
            rejected_records = []

            for raw_entry in all_raw_entries:
                try:
                    std_record = StandardizationService.standardize(raw_entry)
                    is_valid, rejection_reason = ValidationService.validate_record(std_record)
                    if is_valid:
                        valid_records.append(std_record)
                    else:
                        q_entry = QuarantinedRecord(
                            quarantine_id=str(uuid.uuid4()),
                            run_id=run_id,
                            supplier_id=raw_entry["supplier_id"],
                            source_file=raw_entry["file_name"],
                            raw_payload=raw_entry["raw_payload"],
                            rejection_reason=rejection_reason or "VALIDATION_FAILED",
                            quarantined_at=_utc_now()
                        )
                        rejected_records.append(q_entry)
                        session.add(q_entry)
                except Exception as ex:
                    logger.error(f"Error standardizing record {raw_entry.get('record_id')}: {ex}")
                    q_entry = QuarantinedRecord(
                        quarantine_id=str(uuid.uuid4()),
                        run_id=run_id,
                        supplier_id=raw_entry["supplier_id"],
                        source_file=raw_entry["file_name"],
                        raw_payload=raw_entry["raw_payload"],
                        rejection_reason=f"STANDARDIZATION_ERROR: {str(ex)}",
                        quarantined_at=_utc_now()
                    )
                    rejected_records.append(q_entry)
                    session.add(q_entry)

            # 5. ENTITY RESOLUTION
            clusters = EntityResolutionService.resolve_clusters(valid_records)

            # 6. CONFLICT RESOLUTION & LINEAGE GENERATION
            all_lineage_models = []
            for product_id, cluster_records in clusters.items():
                resolved_prod_dict, lineage_decisions = ConflictResolutionService.resolve_cluster_attributes(
                    product_id=product_id,
                    cluster_records=cluster_records
                )

                # Upsert into canonical_products
                existing_product = session.query(CanonicalProduct).filter(
                    CanonicalProduct.product_id == product_id
                ).first()

                if existing_product:
                    for k, v in resolved_prod_dict.items():
                        setattr(existing_product, k, v)
                else:
                    new_product = CanonicalProduct(**resolved_prod_dict)
                    session.add(new_product)

                # Persist Product Identifiers
                if resolved_prod_dict.get("gtin"):
                    session.merge(
                        ProductIdentifier(
                            id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"gtin:{resolved_prod_dict['gtin']}")),
                            product_id=product_id,
                            id_type="GTIN",
                            id_value=resolved_prod_dict["gtin"],
                            supplier_id=resolved_prod_dict.get("supplier_id")
                        )
                    )
                if resolved_prod_dict.get("manufacturer_part_number"):
                    session.merge(
                        ProductIdentifier(
                            id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"mpn:{resolved_prod_dict['brand']}:{resolved_prod_dict['manufacturer_part_number']}")),
                            product_id=product_id,
                            id_type="MPN",
                            id_value=resolved_prod_dict["manufacturer_part_number"],
                            supplier_id=resolved_prod_dict.get("supplier_id")
                        )
                    )

                # Build lineage entities
                lineage_models = LineageService.build_lineage_models(lineage_decisions, run_id=run_id)
                all_lineage_models.extend(lineage_models)

            session.add_all(all_lineage_models)

            # 7. OBSERVABILITY & RECONCILIATION
            duration = round(time.time() - t0, 3)
            completed_time = _utc_now()
            reconciliation_passed = len(all_raw_entries) == (len(valid_records) + len(rejected_records))

            run_metric = PipelineRun(
                run_id=run_id,
                started_at=start_time,
                completed_at=completed_time,
                status="SUCCESS",
                total_input_rows=len(all_raw_entries),
                valid_rows=len(valid_records),
                rejected_rows=len(rejected_records),
                canonical_products_count=len(clusters),
                run_duration_sec=duration,
                reconciliation_passed=reconciliation_passed
            )
            session.add(run_metric)
            session.commit()

            summary = {
                "run_id": run_id,
                "started_at": start_time,
                "completed_at": completed_time,
                "status": "SUCCESS",
                "total_input_rows": len(all_raw_entries),
                "valid_rows": len(valid_records),
                "rejected_rows": len(rejected_records),
                "canonical_products_count": len(clusters),
                "run_duration_sec": duration,
                "reconciliation_passed": reconciliation_passed
            }
            logger.info(
                f"=== Pipeline Run [{run_id}] Finished in {duration}s ===\n"
                f"  Total Ingested: {summary['total_input_rows']}\n"
                f"  Valid Records:  {summary['valid_rows']}\n"
                f"  Quarantined:    {summary['rejected_rows']}\n"
                f"  Canonical Prods:{summary['canonical_products_count']}\n"
                f"  Reconciliation: {'PASS' if reconciliation_passed else 'FAIL'}"
            )
            return summary

        except Exception as ex:
            session.rollback()
            logger.error(f"Pipeline execution failed: {ex}", exc_info=True)
            failed_run = PipelineRun(
                run_id=run_id,
                started_at=start_time,
                completed_at=_utc_now(),
                status="FAILED",
                run_duration_sec=round(time.time() - t0, 3),
                reconciliation_passed=False,
                error_message=str(ex)
            )
            session.add(failed_run)
            session.commit()
            raise ex
        finally:
            if close_session:
                session.close()
