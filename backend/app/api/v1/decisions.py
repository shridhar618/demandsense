from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.schemas import RecommendationOut
from app.services.decision_engine import (
    MissingPrerequisiteError,
    generate_recommendation,
    get_latest_recommendation,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/{product_id}/generate", response_model=RecommendationOut)
def generate(product_id: int, db: Session = Depends(get_db)):
    try:
        rec = generate_recommendation(db, product_id)
    except MissingPrerequisiteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return rec


@router.get("/{product_id}/latest", response_model=RecommendationOut)
def latest(product_id: int, db: Session = Depends(get_db)):
    rec = get_latest_recommendation(db, product_id)
    if not rec:
        raise HTTPException(status_code=404, detail="No recommendation generated yet for this product")
    return rec
