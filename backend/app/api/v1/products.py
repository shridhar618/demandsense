from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import DemandRecord, Product
from app.schemas.schemas import ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    rows = (
        db.query(Product, func.count(DemandRecord.id).label("record_count"))
        .outerjoin(DemandRecord, DemandRecord.product_id == Product.id)
        .filter(Product.is_active == True)  # noqa: E712
        .group_by(Product.id)
        .order_by(Product.name)
        .all()
    )
    out = []
    for product, record_count in rows:
        item = ProductOut.model_validate(product)
        item.record_count = record_count
        out.append(item)
    return out
