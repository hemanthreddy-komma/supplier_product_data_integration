from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from dateutil import parser as dt_parser

from backend.models.schemas import StandardizedRecord

logger = logging.getLogger(__name__)


def _parse_datetime(val: Any) -> datetime:
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        parsed = dt_parser.parse(str(val))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _clean_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _clean_price(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        cleaned = str(val).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot parse price value: '{val}'")


def _clean_stock(val: Any) -> int:
    if val is None or val == "":
        return 0
    try:
        cleaned = str(val).replace(",", "").strip()
        return int(float(cleaned))
    except (ValueError, TypeError):
        raise ValueError(f"Cannot parse stock value: '{val}'")


class StandardizationService:
    """Standardizes disparate supplier fields into a uniform intermediate schema."""

    @classmethod
    def standardize(cls, raw_entry: Dict[str, Any]) -> StandardizedRecord:
        s_id = raw_entry["supplier_id"]
        raw = raw_entry["raw_payload"]
        rec_id = raw_entry["record_id"]
        file_name = raw_entry["file_name"]
        fingerprint = raw_entry["record_fingerprint"]
        source_id = raw_entry.get("source_record_id")

        if s_id == "supplier_a":
            # Supplier A (TechCorp)
            return StandardizedRecord(
                raw_record_id=rec_id,
                supplier_id=s_id,
                file_name=file_name,
                source_record_id=source_id or _clean_str(raw.get("sku_id")),
                record_fingerprint=fingerprint,
                observed_at=_parse_datetime(raw.get("timestamp")),
                gtin=_clean_str(raw.get("barcode_gtin")),
                brand=_clean_str(raw.get("brand_name")),
                manufacturer_part_number=_clean_str(raw.get("manufacturer_pn")),
                product_name=_clean_str(raw.get("product_title")) or "",
                description=_clean_str(raw.get("description")),
                category=_clean_str(raw.get("category_hierarchy")),
                price=_clean_price(raw.get("cost_usd")),
                currency="USD",
                stock_quantity=_clean_stock(raw.get("inventory_count", 0)),
                raw_payload=raw
            )

        elif s_id == "supplier_b":
            # Supplier B (GlobalSupply)
            return StandardizedRecord(
                raw_record_id=rec_id,
                supplier_id=s_id,
                file_name=file_name,
                source_record_id=source_id or _clean_str(raw.get("part_number")),
                record_fingerprint=fingerprint,
                observed_at=_parse_datetime(raw.get("last_updated")),
                gtin=_clean_str(raw.get("upc")),
                brand=_clean_str(raw.get("make")),
                manufacturer_part_number=_clean_str(raw.get("model_no") or raw.get("part_number")),
                product_name=_clean_str(raw.get("product_description")) or "",
                description=_clean_str(raw.get("long_description")),
                category=_clean_str(raw.get("product_dept")),
                price=_clean_price(raw.get("wholesale_price")),
                currency="USD",
                stock_quantity=_clean_stock(raw.get("stock_level", 0)),
                raw_payload=raw
            )

        elif s_id == "supplier_c":
            # Supplier C (ApexGoods)
            return StandardizedRecord(
                raw_record_id=rec_id,
                supplier_id=s_id,
                file_name=file_name,
                source_record_id=source_id or _clean_str(raw.get("item_ref")),
                record_fingerprint=fingerprint,
                observed_at=_parse_datetime(raw.get("feed_timestamp")),
                gtin=_clean_str(raw.get("ean_13")),
                brand=_clean_str(raw.get("brand")),
                manufacturer_part_number=_clean_str(raw.get("mpn") or raw.get("item_ref")),
                product_name=_clean_str(raw.get("name")) or "",
                description=_clean_str(raw.get("item_details")),
                category=_clean_str(raw.get("category_path")),
                price=_clean_price(raw.get("retail_price")),
                currency="USD",
                stock_quantity=_clean_stock(raw.get("qty_available", 0)),
                raw_payload=raw
            )

        else:
            # Generic mapping
            return StandardizedRecord(
                raw_record_id=rec_id,
                supplier_id=s_id,
                file_name=file_name,
                source_record_id=source_id or _clean_str(raw.get("id")),
                record_fingerprint=fingerprint,
                observed_at=_parse_datetime(raw.get("timestamp") or raw.get("updated_at")),
                gtin=_clean_str(raw.get("gtin") or raw.get("upc") or raw.get("ean")),
                brand=_clean_str(raw.get("brand")),
                manufacturer_part_number=_clean_str(raw.get("mpn") or raw.get("sku")),
                product_name=_clean_str(raw.get("name") or raw.get("title")) or "",
                description=_clean_str(raw.get("description")),
                category=_clean_str(raw.get("category")),
                price=_clean_price(raw.get("price", 0.0)),
                currency="USD",
                stock_quantity=_clean_stock(raw.get("stock", 0)),
                raw_payload=raw
            )
