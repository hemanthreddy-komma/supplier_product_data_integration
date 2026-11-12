from datetime import datetime, timezone
import pytest
from backend.models.schemas import StandardizedRecord
from backend.services.resolution import EntityResolutionService


def test_gtin_resolution_matching():
    now = datetime.now(timezone.utc)
    rec1 = StandardizedRecord(
        raw_record_id="r1",
        supplier_id="supplier_a",
        file_name="feed_a.json",
        record_fingerprint="fp1",
        observed_at=now,
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Headphones A",
        price=398.0,
        stock_quantity=10,
        raw_payload={}
    )
    rec2 = StandardizedRecord(
        raw_record_id="r2",
        supplier_id="supplier_b",
        file_name="feed_b.csv",
        record_fingerprint="fp2",
        observed_at=now,
        gtin="04006381333931",  # Same GTIN
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Headphones B",
        price=389.0,
        stock_quantity=20,
        raw_payload={}
    )

    clusters = EntityResolutionService.resolve_clusters([rec1, rec2])
    # Both records should be merged into exactly 1 cluster
    assert len(clusters) == 1
    cluster_records = list(clusters.values())[0]
    assert len(cluster_records) == 2


def test_brand_mpn_fallback_resolution():
    now = datetime.now(timezone.utc)
    # Neither has GTIN, but matching Brand and MPN
    rec1 = StandardizedRecord(
        raw_record_id="r3",
        supplier_id="supplier_b",
        file_name="feed_b.csv",
        record_fingerprint="fp3",
        observed_at=now,
        gtin=None,
        brand="Logitech",
        manufacturer_part_number="910-006556",
        product_name="Logitech Mouse",
        price=92.0,
        stock_quantity=50,
        raw_payload={}
    )
    rec2 = StandardizedRecord(
        raw_record_id="r4",
        supplier_id="supplier_c",
        file_name="feed_c.json",
        record_fingerprint="fp4",
        observed_at=now,
        gtin=None,
        brand="logitech ",  # Case and whitespace variations
        manufacturer_part_number=" 910-006556",
        product_name="Logitech Wireless Mouse",
        price=99.0,
        stock_quantity=40,
        raw_payload={}
    )

    clusters = EntityResolutionService.resolve_clusters([rec1, rec2])
    # Should merge into 1 cluster based on normalized brand + MPN
    assert len(clusters) == 1
    cluster_records = list(clusters.values())[0]
    assert len(cluster_records) == 2


def test_ambiguous_different_products_do_not_merge():
    now = datetime.now(timezone.utc)
    rec_sony = StandardizedRecord(
        raw_record_id="r5",
        supplier_id="supplier_a",
        file_name="feed_a.json",
        record_fingerprint="fp5",
        observed_at=now,
        gtin="04006381333931",
        brand="Sony",
        manufacturer_part_number="WH1000XM5",
        product_name="Sony Headphones",
        price=398.0,
        stock_quantity=10,
        raw_payload={}
    )
    rec_apple = StandardizedRecord(
        raw_record_id="r6",
        supplier_id="supplier_a",
        file_name="feed_a.json",
        record_fingerprint="fp6",
        observed_at=now,
        gtin=None,
        brand="Apple",
        manufacturer_part_number="MLY33LL/A",
        product_name="Apple MacBook Air",
        price=1099.0,
        stock_quantity=5,
        raw_payload={}
    )

    clusters = EntityResolutionService.resolve_clusters([rec_sony, rec_apple])
    # Different products must NOT be merged
    assert len(clusters) == 2
