import json
import pytest
from pathlib import Path
from backend.services.ingestion import IngestionService, compute_payload_fingerprint


def test_csv_ingestion(tmp_path):
    csv_file = tmp_path / "feed.csv"
    csv_file.write_text("part_number,product_description,wholesale_price\nGS-001,Monitor,299.99\nGS-002,Mouse,19.99", encoding="utf-8")
    
    records, count = IngestionService.parse_feed_file(csv_file, "supplier_b")
    assert count == 2
    assert records[0]["supplier_id"] == "supplier_b"
    assert records[0]["source_record_id"] == "GS-001"
    assert records[0]["raw_payload"]["product_description"] == "Monitor"
    assert len(records[0]["record_fingerprint"]) == 64


def test_json_ingestion(tmp_path):
    json_file = tmp_path / "feed.json"
    data = [
        {"sku_id": "TC-001", "product_title": "Laptop", "cost_usd": 899.0},
        {"sku_id": "TC-002", "product_title": "Headphones", "cost_usd": 149.0}
    ]
    json_file.write_text(json.dumps(data), encoding="utf-8")

    records, count = IngestionService.parse_feed_file(json_file, "supplier_a")
    assert count == 2
    assert records[0]["supplier_id"] == "supplier_a"
    assert records[0]["source_record_id"] == "TC-001"
    assert records[0]["raw_payload"]["product_title"] == "Laptop"


def test_empty_input_file(tmp_path):
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")
    records, count = IngestionService.parse_feed_file(empty_json, "supplier_a")
    assert count == 0
    assert len(records) == 0


def test_missing_input_file():
    with pytest.raises(FileNotFoundError):
        IngestionService.parse_feed_file(Path("non_existent_feed.json"), "supplier_a")


def test_unsupported_format(tmp_path):
    bad_file = tmp_path / "feed.txt"
    bad_file.write_text("some random data", encoding="utf-8")
    with pytest.raises(ValueError):
        IngestionService.parse_feed_file(bad_file, "supplier_a")


def test_payload_fingerprint_stability():
    p1 = {"name": "Widget", "price": 10.0, "category": "Tools"}
    p2 = {"price": 10.0, "category": "Tools", "name": "Widget"}
    assert compute_payload_fingerprint(p1) == compute_payload_fingerprint(p2)


def test_excel_ingestion(tmp_path):
    import pandas as pd
    excel_file = tmp_path / "feed.xlsx"
    df = pd.DataFrame([
        {"sku": "EX-001", "name": "Smart Watch", "price": "199.99"},
        {"sku": "EX-002", "name": "Wireless Charger", "price": "29.99"}
    ])
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    records, count = IngestionService.parse_feed_file(excel_file, "supplier_b")
    assert count == 2
    assert records[0]["supplier_id"] == "supplier_b"
    assert records[0]["source_record_id"] == "EX-001"
    assert records[0]["raw_payload"]["name"] == "Smart Watch"
    assert len(records[0]["record_fingerprint"]) == 64
