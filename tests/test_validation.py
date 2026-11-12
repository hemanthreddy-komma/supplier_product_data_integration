from datetime import datetime, timezone
import pytest
from backend.models.schemas import StandardizedRecord
from backend.services.validation import ValidationService, validate_gs1_checksum


def test_gtin_checksum_validation():
    # Valid EAN-13 (4006381333931)
    is_valid, normalized = validate_gs1_checksum("4006381333931")
    assert is_valid is True
    assert normalized == "04006381333931"

    # Invalid check digit
    is_valid_bad, _ = validate_gs1_checksum("4006381333939")
    assert is_valid_bad is False

    # Non-digit
    is_valid_alpha, _ = validate_gs1_checksum("ABC123456789")
    assert is_valid_alpha is False

    # None
    is_valid_none, _ = validate_gs1_checksum(None)
    assert is_valid_none is False


def test_validation_happy_path():
    rec = StandardizedRecord(
        raw_record_id="rec-001",
        supplier_id="supplier_a",
        file_name="feed.json",
        record_fingerprint="fp1",
        observed_at=datetime.now(timezone.utc),
        gtin="4006381333931",
        brand="Sony",
        manufacturer_part_number="WH-1000",
        product_name="Sony Wireless Headphones",
        price=349.99,
        stock_quantity=15,
        raw_payload={}
    )
    is_valid, reason = ValidationService.validate_record(rec)
    assert is_valid is True
    assert reason is None
    assert rec.gtin == "04006381333931"


def test_validation_empty_product_name():
    rec = StandardizedRecord(
        raw_record_id="rec-002",
        supplier_id="supplier_a",
        file_name="feed.json",
        record_fingerprint="fp2",
        observed_at=datetime.now(timezone.utc),
        gtin="4006381333931",
        brand="Sony",
        manufacturer_part_number="WH-1000",
        product_name="   ",  # Blank
        price=349.99,
        stock_quantity=15,
        raw_payload={}
    )
    is_valid, reason = ValidationService.validate_record(rec)
    assert is_valid is False
    assert "MISSING_PRODUCT_NAME" in reason


def test_validation_invalid_price():
    rec = StandardizedRecord(
        raw_record_id="rec-003",
        supplier_id="supplier_b",
        file_name="feed.csv",
        record_fingerprint="fp3",
        observed_at=datetime.now(timezone.utc),
        gtin="4006381333931",
        brand="Sony",
        manufacturer_part_number="WH-1000",
        product_name="Sony Headphones",
        price=-10.0,  # Negative price
        stock_quantity=15,
        raw_payload={}
    )
    is_valid, reason = ValidationService.validate_record(rec)
    assert is_valid is False
    assert "INVALID_PRICE" in reason


def test_validation_invalid_stock():
    rec = StandardizedRecord(
        raw_record_id="rec-004",
        supplier_id="supplier_b",
        file_name="feed.csv",
        record_fingerprint="fp4",
        observed_at=datetime.now(timezone.utc),
        gtin="4006381333931",
        brand="Sony",
        manufacturer_part_number="WH-1000",
        product_name="Sony Headphones",
        price=199.0,
        stock_quantity=-2,  # Negative stock
        raw_payload={}
    )
    is_valid, reason = ValidationService.validate_record(rec)
    assert is_valid is False
    assert "INVALID_STOCK" in reason


def test_validation_missing_all_identifiers():
    rec = StandardizedRecord(
        raw_record_id="rec-005",
        supplier_id="supplier_c",
        file_name="feed.json",
        record_fingerprint="fp5",
        observed_at=datetime.now(timezone.utc),
        gtin=None,
        brand=None,
        manufacturer_part_number=None,
        product_name="Mystery Part",
        price=49.99,
        stock_quantity=5,
        raw_payload={}
    )
    is_valid, reason = ValidationService.validate_record(rec)
    assert is_valid is False
    assert "MISSING_IDENTIFIER" in reason
