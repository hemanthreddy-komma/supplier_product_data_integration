import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.config import settings
from backend.database.models import SourceFile, Supplier
from backend.models.schemas import PipelineRunSummary, SupplierConfigOut, UploadResponse
from backend.services.ingestion import IngestionService
from backend.services.pipeline import PipelineService

router = APIRouter(prefix="/api/uploads", tags=["Uploads & Pipeline"])


@router.get("/suppliers", response_model=List[SupplierConfigOut])
def get_supplier_configs(db: Session = Depends(get_db)):
    """Fetch current supplier priority settings."""
    suppliers = db.query(Supplier).order_by(Supplier.priority.asc()).all()
    return suppliers


@router.post("/{supplier_id}", response_model=UploadResponse)
async def upload_supplier_feed(
    supplier_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a supplier CSV or JSON feed file."""
    if supplier_id not in settings.SUPPLIER_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid supplier ID: {supplier_id}")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".json", ".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Only .json, .csv, .xlsx, and .xls files are supported.")

    file_id = str(uuid.uuid4())
    save_filename = f"{supplier_id}_{file_id[:8]}{ext}"
    dest_path = settings.RAW_DATA_DIR / save_filename

    # Save uploaded file
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = dest_path.stat().st_size

    # Validate parsing
    try:
        _, record_count = IngestionService.parse_feed_file(dest_path, supplier_id)
    except Exception as ex:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded feed: {ex}")

    # Register in source_files table
    source_file = SourceFile(
        file_id=file_id,
        supplier_id=supplier_id,
        file_name=file.filename,
        file_format=ext.replace(".", ""),
        file_size_bytes=file_size,
        record_count=record_count
    )
    db.add(source_file)
    db.commit()

    # Also update active default file for supplier
    default_dest = settings.RAW_DATA_DIR / f"{supplier_id}{ext}"
    shutil.copyfile(dest_path, default_dest)

    return UploadResponse(
        file_id=file_id,
        file_name=file.filename,
        supplier_id=supplier_id,
        file_format=ext.replace(".", ""),
        file_size_bytes=file_size,
        record_count=record_count,
        message="File uploaded and validated successfully."
    )


@router.post("/pipeline/run", response_model=PipelineRunSummary)
def trigger_pipeline(db: Session = Depends(get_db)):
    """Triggers the full integration pipeline across current raw supplier feeds."""
    try:
        pipeline = PipelineService(db_session=db)
        summary = pipeline.execute_pipeline()
        return summary
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Pipeline run failed: {str(ex)}")
