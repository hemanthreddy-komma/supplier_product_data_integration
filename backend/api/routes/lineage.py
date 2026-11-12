from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.database.models import AttributeLineage
from backend.models.schemas import AttributeLineageOut

router = APIRouter(prefix="/api/lineage", tags=["Attribute Lineage"])


@router.get("", response_model=List[AttributeLineageOut])
def get_all_lineage(
    product_id: Optional[str] = Query(None, description="Filter lineage by canonical product ID"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(AttributeLineage)
    if product_id:
        query = query.filter(AttributeLineage.product_id == product_id)
    return query.order_by(AttributeLineage.recorded_at.desc()).limit(limit).all()


@router.get("/product/{product_id}", response_model=List[AttributeLineageOut])
def get_product_lineage(product_id: str, db: Session = Depends(get_db)):
    """Fetch all attribute-level provenance entries for a specific product."""
    entries = db.query(AttributeLineage).filter(
        AttributeLineage.product_id == product_id
    ).order_by(AttributeLineage.attribute_name.asc()).all()
    if not entries:
        raise HTTPException(status_code=404, detail=f"No lineage records found for product ID {product_id}")
    return entries
