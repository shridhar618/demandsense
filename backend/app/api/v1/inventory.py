from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import InventorySnapshot
from app.schemas.schemas import (
    InventoryIntelligenceResponse,
    InventorySnapshotOut,
    InventoryUploadResponse,
)
from app.services.inventory_intelligence_service import compute_inventory_intelligence
from app.services.inventory_service import ingest_inventory_csv

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/upload", response_model=InventoryUploadResponse)
async def upload_inventory(file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = ingest_inventory_csv(db, filename=file.filename, file_bytes=file_bytes)
    return InventoryUploadResponse(**result)


@router.get("/intelligence", response_model=InventoryIntelligenceResponse)
def get_inventory_intelligence(db: Session = Depends(get_db)):
    result = compute_inventory_intelligence(db)
    return result


@router.get("/{product_id}", response_model=InventorySnapshotOut)
def get_inventory(product_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(InventorySnapshot).filter(InventorySnapshot.product_id == product_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No inventory snapshot for this product")
    return snapshot
