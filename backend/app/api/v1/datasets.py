from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Dataset
from app.schemas.schemas import DatasetProfile
from app.services.ingestion_service import ingest_csv

router = APIRouter(prefix="/datasets", tags=["datasets"])

ALLOWED_EXTENSIONS = (".csv",)


@router.post("/upload", response_model=DatasetProfile)
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only .csv files are supported in this phase")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    dataset = ingest_csv(db, filename=file.filename, file_bytes=file_bytes)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetProfile)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("", response_model=list[DatasetProfile])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
