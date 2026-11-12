from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id: Mapped[str] = mapped_column(sa.String(50), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    default_format: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    # Relationships
    source_files: Mapped[List["SourceFile"]] = relationship("SourceFile", back_populates="supplier")
    raw_records: Mapped[List["RawSupplierRecord"]] = relationship("RawSupplierRecord", back_populates="supplier")


class SourceFile(Base):
    __tablename__ = "source_files"

    file_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(sa.String(50), sa.ForeignKey("suppliers.supplier_id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(sa.BigInteger, nullable=True)
    record_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="source_files")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    total_input_rows: Mapped[int] = mapped_column(sa.Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(sa.Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(sa.Integer, default=0)
    canonical_products_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    run_duration_sec: Mapped[float] = mapped_column(sa.Float, default=0.0)
    reconciliation_passed: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)


class RawSupplierRecord(Base):
    __tablename__ = "raw_supplier_records"

    record_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(sa.String(50), sa.ForeignKey("suppliers.supplier_id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[Optional[str]] = mapped_column(sa.String(64), sa.ForeignKey("source_files.file_id", ondelete="SET NULL"), nullable=True)
    source_record_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    record_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(sa.JSON, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    __table_args__ = (
        sa.UniqueConstraint("supplier_id", "record_fingerprint", name="uq_supplier_record_fingerprint"),
        sa.Index("idx_raw_supplier_run", "supplier_id", "run_id"),
    )

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="raw_records")


class CanonicalProduct(Base):
    __tablename__ = "canonical_products"

    product_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    product_name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    brand: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    manufacturer_part_number: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    gtin: Mapped[Optional[str]] = mapped_column(sa.String(14), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    price: Mapped[float] = mapped_column(sa.Float, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(10), default="USD")
    stock_quantity: Mapped[int] = mapped_column(sa.Integer, default=0)
    supplier_id: Mapped[Optional[str]] = mapped_column(sa.String(50), sa.ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True)
    source_suppliers: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    status: Mapped[str] = mapped_column(sa.String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        sa.Index("idx_canonical_gtin", "gtin"),
        sa.Index("idx_canonical_brand_mpn", "brand", "manufacturer_part_number"),
        sa.Index("idx_canonical_name", "product_name"),
    )

    identifiers: Mapped[List["ProductIdentifier"]] = relationship("ProductIdentifier", back_populates="product", cascade="all, delete-orphan")
    lineage_entries: Mapped[List["AttributeLineage"]] = relationship("AttributeLineage", back_populates="product", cascade="all, delete-orphan")


class ProductIdentifier(Base):
    __tablename__ = "product_identifiers"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("canonical_products.product_id", ondelete="CASCADE"), nullable=False)
    id_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    id_value: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    supplier_id: Mapped[Optional[str]] = mapped_column(sa.String(50), sa.ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    __table_args__ = (
        sa.UniqueConstraint("product_id", "id_type", "id_value", name="uq_product_identifier"),
        sa.Index("idx_identifiers_value", "id_type", "id_value"),
    )

    product: Mapped["CanonicalProduct"] = relationship("CanonicalProduct", back_populates="identifiers")


class AttributeLineage(Base):
    __tablename__ = "attribute_lineage"

    lineage_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("canonical_products.product_id", ondelete="CASCADE"), nullable=False)
    attribute_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    selected_value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    original_source_value: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    supplier_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_file: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_record_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    source_timestamp: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    run_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    selection_reason: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    __table_args__ = (
        sa.Index("idx_lineage_product_id", "product_id"),
    )

    product: Mapped["CanonicalProduct"] = relationship("CanonicalProduct", back_populates="lineage_entries")


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_records"

    quarantine_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(sa.String(64), sa.ForeignKey("pipeline_runs.run_id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(sa.String(50), sa.ForeignKey("suppliers.supplier_id", ondelete="CASCADE"), nullable=False)
    source_file: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(sa.JSON, nullable=False)
    rejection_reason: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    quarantined_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utc_now)

    __table_args__ = (
        sa.Index("idx_quarantine_run", "run_id"),
    )
