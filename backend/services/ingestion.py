import csv
import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def compute_payload_fingerprint(payload: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 fingerprint for a payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class IngestionService:
    """
    Tier 2 Service: Ingests CSV and JSON feeds, creates stable fingerprints,
    and captures source metadata.
    """

    @staticmethod
    def parse_feed_file(file_path: Path, supplier_id: str) -> Tuple[List[Dict[str, Any]], int]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Feed file not found: {file_path}")

        suffix = file_path.suffix.lower()
        records: List[Dict[str, Any]] = []

        if suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("items") or data.get("products") or [data]
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    fingerprint = compute_payload_fingerprint(item)
                    source_id = str(item.get("sku_id") or item.get("item_ref") or item.get("id") or "")
                    records.append({
                        "record_id": str(uuid.uuid4()),
                        "supplier_id": supplier_id,
                        "file_name": file_path.name,
                        "source_record_id": source_id if source_id else None,
                        "record_fingerprint": fingerprint,
                        "raw_payload": item
                    })

        elif suffix == ".csv":
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_dict = dict(row)
                    fingerprint = compute_payload_fingerprint(row_dict)
                    source_id = str(row_dict.get("part_number") or row_dict.get("sku") or row_dict.get("id") or "")
                    records.append({
                        "record_id": str(uuid.uuid4()),
                        "supplier_id": supplier_id,
                        "file_name": file_path.name,
                        "source_record_id": source_id if source_id else None,
                        "record_fingerprint": fingerprint,
                        "raw_payload": row_dict
                    })

        elif suffix in [".xlsx", ".xls"]:
            import pandas as pd
            # Ingest Excel spreadsheet sheets
            df = pd.read_excel(file_path, dtype=str)
            df = df.where(pd.notnull(df), None)
            for row in df.to_dict(orient="records"):
                row_dict = {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in row.items()}
                fingerprint = compute_payload_fingerprint(row_dict)
                source_id = str(
                    row_dict.get("sku") or row_dict.get("part_number") or row_dict.get("model_no") or 
                    row_dict.get("id") or row_dict.get("item_ref") or ""
                )
                records.append({
                    "record_id": str(uuid.uuid4()),
                    "supplier_id": supplier_id,
                    "file_name": file_path.name,
                    "source_record_id": source_id if source_id else None,
                    "record_fingerprint": fingerprint,
                    "raw_payload": row_dict
                })
        else:
            raise ValueError(f"Unsupported feed file format: {suffix}. Supported formats: .json, .csv, .xlsx, .xls")

        logger.info(f"Ingested {len(records)} records from {file_path.name} for supplier '{supplier_id}'.")
        return records, len(records)
