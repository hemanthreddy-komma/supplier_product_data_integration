from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Tuple
from backend.config import settings
from backend.models.schemas import StandardizedRecord

logger = logging.getLogger(__name__)


class ConflictResolutionService:
    """
    Tier 2 Service: Resolves conflicting product attributes using configurable
    supplier priority and timestamps.
    """

    @classmethod
    def resolve_cluster_attributes(
        cls, product_id: str, cluster_records: List[StandardizedRecord]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Resolves conflicts for a single product cluster.
        Returns:
          - resolved_product_dict: CanonicalProduct fields
          - lineage_decisions: list of lineage audit dictionaries
        """
        # Sort cluster records by:
        # 1. Supplier priority (1 is highest, so lowest integer first)
        # 2. Observed timestamp (newest first)
        def sort_key(r: StandardizedRecord):
            prio = settings.SUPPLIER_PRIORITIES.get(r.supplier_id, 99)
            ts = r.observed_at.timestamp() if r.observed_at else 0.0
            return (prio, -ts)

        sorted_records = sorted(cluster_records, key=sort_key)
        primary_record = sorted_records[0]

        contributing_suppliers = sorted(list({r.supplier_id for r in sorted_records}))
        source_suppliers_str = ", ".join(contributing_suppliers)

        lineage_decisions: List[Dict[str, Any]] = []

        # Attribute resolution helper
        def select_attribute(
            attr_name: str, fallback_val: Any = None
        ) -> Tuple[Any, StandardizedRecord, str]:
            for rec in sorted_records:
                val = getattr(rec, attr_name, None)
                if val is not None and str(val).strip() != "":
                    prio = settings.SUPPLIER_PRIORITIES.get(rec.supplier_id, 99)
                    if rec.supplier_id == primary_record.supplier_id:
                        reason = f"SUPPLIER_PRIORITY: {rec.supplier_id} (Priority {prio})"
                    else:
                        reason = f"ATTRIBUTE_FALLBACK: {rec.supplier_id} provided non-null value"
                    return val, rec, reason
            return fallback_val, primary_record, "DEFAULT_VALUE"

        # Resolve core attributes
        p_name, name_rec, name_reason = select_attribute("product_name", "Unnamed Product")
        brand, brand_rec, brand_reason = select_attribute("brand", "Generic")
        mpn, mpn_rec, mpn_reason = select_attribute("manufacturer_part_number", "UNKNOWN")
        gtin, gtin_rec, gtin_reason = select_attribute("gtin")
        category, cat_rec, cat_reason = select_attribute("category", "General")
        description, desc_rec, desc_reason = select_attribute("description", "")
        price, price_rec, price_reason = select_attribute("price", 0.0)
        stock, stock_rec, stock_reason = select_attribute("stock_quantity", 0)

        # Track decisions for lineage
        tracked_attributes = [
            ("product_name", p_name, name_rec, name_reason),
            ("brand", brand, brand_rec, brand_reason),
            ("manufacturer_part_number", mpn, mpn_rec, mpn_reason),
            ("category", category, cat_rec, cat_reason),
            ("price", f"{float(price):.2f}", price_rec, price_reason),
            ("stock_quantity", str(stock), stock_rec, stock_reason),
        ]
        if gtin:
            tracked_attributes.append(("gtin", str(gtin), gtin_rec, gtin_reason))
        if description:
            tracked_attributes.append(("description", str(description), desc_rec, desc_reason))

        for attr, win_val, win_rec, reason in tracked_attributes:
            lineage_decisions.append({
                "product_id": product_id,
                "attribute_name": attr,
                "selected_value": str(win_val),
                "original_source_value": str(win_rec.raw_payload.get(attr) or win_val),
                "supplier_name": settings.SUPPLIER_NAMES.get(win_rec.supplier_id, win_rec.supplier_id),
                "source_file": win_rec.file_name,
                "source_record_id": win_rec.source_record_id,
                "source_timestamp": win_rec.observed_at,
                "selection_reason": reason
            })

        now = datetime.now(timezone.utc)
        resolved_product = {
            "product_id": product_id,
            "product_name": str(p_name),
            "brand": str(brand),
            "manufacturer_part_number": str(mpn),
            "gtin": str(gtin) if gtin else None,
            "category": str(category),
            "description": str(description) if description else None,
            "price": round(float(price), 2),
            "currency": "USD",
            "stock_quantity": int(stock),
            "supplier_id": primary_record.supplier_id,
            "source_suppliers": source_suppliers_str,
            "status": "ACTIVE",
            "created_at": primary_record.observed_at or now,
            "updated_at": now
        }

        return resolved_product, lineage_decisions
