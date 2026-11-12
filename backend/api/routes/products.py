import io
from typing import List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from backend.api.dependencies import get_db
from backend.database.models import CanonicalProduct
from backend.models.schemas import CanonicalProductOut

router = APIRouter(prefix="/api/products", tags=["Canonical Products"])


@router.get("", response_model=List[CanonicalProductOut])
def get_products(
    search: Optional[str] = Query(None, description="Search term for name, brand, MPN, or GTIN"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(CanonicalProduct)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CanonicalProduct.product_name.ilike(s),
                CanonicalProduct.brand.ilike(s),
                CanonicalProduct.manufacturer_part_number.ilike(s),
                CanonicalProduct.gtin.ilike(s)
            )
        )

    if brand and brand != "All":
        query = query.filter(CanonicalProduct.brand == brand)

    if category and category != "All":
        query = query.filter(CanonicalProduct.category == category)

    products = query.order_by(CanonicalProduct.updated_at.desc()).offset(offset).limit(limit).all()
    return products


@router.get("/summary/stats")
def get_product_stats(db: Session = Depends(get_db)):
    """Summary metrics of the canonical catalog."""
    total_count = db.query(CanonicalProduct).count()
    if total_count == 0:
        return {
            "total_products": 0,
            "total_brands": 0,
            "total_stock": 0,
            "avg_price": 0.0,
            "brands": [],
            "categories": []
        }

    total_stock = db.query(func.sum(CanonicalProduct.stock_quantity)).scalar() or 0
    avg_price = db.query(func.avg(CanonicalProduct.price)).scalar() or 0.0
    brands = [b[0] for b in db.query(CanonicalProduct.brand).distinct().order_by(CanonicalProduct.brand).all() if b[0]]
    categories = [c[0] for c in db.query(CanonicalProduct.category).distinct().order_by(CanonicalProduct.category).all() if c[0]]

    return {
        "total_products": total_count,
        "total_brands": len(brands),
        "total_stock": int(total_stock),
        "avg_price": round(float(avg_price), 2),
        "brands": brands,
        "categories": categories
    }


@router.get("/export/csv")
def export_products_csv(db: Session = Depends(get_db)):
    """Exports canonical catalog to CSV."""
    products = db.query(CanonicalProduct).order_by(CanonicalProduct.updated_at.desc()).all()
    if not products:
        return Response(content="No products found", media_type="text/plain")

    data = [
        {
            "product_id": p.product_id,
            "product_name": p.product_name,
            "brand": p.brand,
            "manufacturer_part_number": p.manufacturer_part_number,
            "gtin": p.gtin or "",
            "category": p.category or "",
            "description": p.description or "",
            "price": p.price,
            "currency": p.currency,
            "stock_quantity": p.stock_quantity,
            "source_suppliers": p.source_suppliers or "",
            "status": p.status,
            "updated_at": p.updated_at.isoformat() if p.updated_at else ""
        }
        for p in products
    ]
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=canonical_catalog.csv"}
    )


@router.get("/export/excel")
def export_products_excel(db: Session = Depends(get_db)):
    """Exports canonical catalog to formatted Excel (.xlsx) file."""
    products = db.query(CanonicalProduct).order_by(CanonicalProduct.updated_at.desc()).all()
    if not products:
        return Response(content="No products found", media_type="text/plain")

    data = [
        {
            "Product ID": p.product_id,
            "Product Name": p.product_name,
            "Brand": p.brand,
            "MPN / Model": p.manufacturer_part_number,
            "GTIN / Barcode": p.gtin or "",
            "Category": p.category or "",
            "Description": p.description or "",
            "Price ($)": p.price,
            "Currency": p.currency,
            "Stock Qty": p.stock_quantity,
            "Source Suppliers": p.source_suppliers or "",
            "Status": p.status,
            "Last Updated": p.updated_at.isoformat() if p.updated_at else ""
        }
        for p in products
    ]
    df = pd.DataFrame(data)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Canonical Catalog")
        
        # Format columns width
        worksheet = writer.sheets["Canonical Catalog"]
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    excel_buffer.seek(0)
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=canonical_catalog.xlsx"}
    )


@router.get("/{product_id}", response_model=CanonicalProductOut)
def get_product_by_id(product_id: str, db: Session = Depends(get_db)):
    product = db.query(CanonicalProduct).filter(CanonicalProduct.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
