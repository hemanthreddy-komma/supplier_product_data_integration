from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StandardizedRecord(BaseModel):
    """Intermediate model for standardized records before entity resolution."""
    raw_record_id: str
    supplier_id: str
    file_name: str
    source_record_id: Optional[str] = None
    record_fingerprint: str
    observed_at: datetime
    
    # Core Identifiers
    gtin: Optional[str] = None
    brand: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    
    # Attributes
    product_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float
    currency: str = "USD"
    stock_quantity: int = 0
    
    # Raw source payload
    raw_payload: Dict[str, Any]


class CanonicalProductOut(BaseModel):
    product_id: str
    product_name: str
    brand: str
    manufacturer_part_number: str
    gtin: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    stock_quantity: int
    supplier_id: Optional[str] = None
    source_suppliers: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttributeLineageOut(BaseModel):
    lineage_id: str
    product_id: str
    attribute_name: str
    selected_value: str
    original_source_value: Optional[str] = None
    supplier_name: str
    source_file: str
    source_record_id: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    run_id: str
    selection_reason: str
    recorded_at: datetime

    class Config:
        from_attributes = True


class QuarantinedRecordOut(BaseModel):
    quarantine_id: str
    run_id: str
    supplier_id: str
    source_file: str
    raw_payload: Dict[str, Any]
    rejection_reason: str
    quarantined_at: datetime

    class Config:
        from_attributes = True


class PipelineRunSummary(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    total_input_rows: int
    valid_rows: int
    rejected_rows: int
    canonical_products_count: int
    run_duration_sec: float
    reconciliation_passed: bool
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    file_id: str
    file_name: str
    supplier_id: str
    file_format: str
    file_size_bytes: int
    record_count: int
    message: str


class SupplierConfigOut(BaseModel):
    supplier_id: str
    name: str
    priority: int
    default_format: str
