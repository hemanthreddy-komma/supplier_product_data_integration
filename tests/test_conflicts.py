from datetime import datetime, timedelta, timezone
import pytest
from backend.models.schemas import StandardizedRecord
from backend.services.conflict_resolution import ConflictResolutionService


def test_supplier_priority_conflict_resolution():
    now = datetime.now(timezone.utc)
    # Supplier A has Priority 1, price $398.00, missing description
    rec_a = StandardizedRecord(
        raw_record_id="ra",
        supplier_id="supplier_a",
        file_name="supplier_a.json",
        record_fingerprint="fpa",
        observed_at=now - timedelta(hours=2),
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony WH-1000XM5 Headphones",
        description=None,  # Missing
        price=398.00,
        stock_quantity=50,
        raw_payload={"cost_usd": 398.00}
    )

    # Supplier B has Priority 2, price $389.00, rich description provided
    rec_b = StandardizedRecord(
        raw_record_id="rb",
        supplier_id="supplier_b",
        file_name="supplier_b.csv",
        record_fingerprint="fpb",
        observed_at=now - timedelta(hours=1),
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Wireless Headset",
        description="Premium noise canceling headphones.",
        price=389.00,
        stock_quantity=40,
        raw_payload={"wholesale_price": 389.00, "long_description": "Premium noise canceling headphones."}
    )

    resolved, lineage = ConflictResolutionService.resolve_cluster_attributes("prod-001", [rec_a, rec_b])

    # 1. Supplier A Priority 1 wins the price
    assert resolved["price"] == 398.00
    assert resolved["supplier_id"] == "supplier_a"

    # 2. Supplier B provides description fallback
    assert resolved["description"] == "Premium noise canceling headphones."

    # 3. Lineage checks
    price_lineage = [l for l in lineage if l["attribute_name"] == "price"][0]
    assert price_lineage["selected_value"] == "398.00"
    assert "SUPPLIER_PRIORITY: supplier_a" in price_lineage["selection_reason"]

    desc_lineage = [l for l in lineage if l["attribute_name"] == "description"][0]
    assert desc_lineage["selected_value"] == "Premium noise canceling headphones."
    assert "ATTRIBUTE_FALLBACK: supplier_b" in desc_lineage["selection_reason"]


def test_timestamp_tie_breaker_same_supplier():
    now = datetime.now(timezone.utc)
    # Same supplier, older record
    rec_old = StandardizedRecord(
        raw_record_id="r_old",
        supplier_id="supplier_a",
        file_name="old.json",
        record_fingerprint="fp_old",
        observed_at=now - timedelta(days=2),
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Headphones (Old Name)",
        price=420.00,
        stock_quantity=10,
        raw_payload={}
    )
    # Same supplier, newer record
    rec_new = StandardizedRecord(
        raw_record_id="r_new",
        supplier_id="supplier_a",
        file_name="new.json",
        record_fingerprint="fp_new",
        observed_at=now,
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Headphones (New Name)",
        price=398.00,
        stock_quantity=30,
        raw_payload={}
    )

    resolved, _ = ConflictResolutionService.resolve_cluster_attributes("prod-002", [rec_old, rec_new])
    # Newer timestamp wins within the same supplier
    assert resolved["product_name"] == "Sony Headphones (New Name)"
    assert resolved["price"] == 398.00
