from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Product
from app.schemas.schemas import (
    ForecastPointOut,
    ForecastSeriesResponse,
    ModelMetrics,
    TrainForecastRequest,
    TrainForecastResponse,
)
from app.services.forecasting_service import (
    InsufficientHistoryError,
    get_latest_forecast,
    train_and_compare,
)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.post("/train", response_model=TrainForecastResponse)
def train_forecast(payload: TrainForecastRequest, db: Session = Depends(get_db)):
    try:
        result = train_and_compare(db, payload.product_id, payload.horizon_days)
    except InsufficientHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    models = [
        ModelMetrics(
            model_type=run.model_type,
            mae=run.mae,
            rmse=run.rmse,
            mape=run.mape,
            training_time_ms=run.training_time_ms,
            is_best=run.is_best,
            feature_importance=run.feature_importance,
            forecast_run_id=run.id,
        )
        for run in result["runs"]
    ]
    return TrainForecastResponse(
        product_id=result["product_id"],
        comparison_batch_id=result["comparison_batch_id"],
        models=models,
        best_model=result["best_model"],
    )


@router.get("/{product_id}/latest", response_model=ForecastSeriesResponse)
def latest_forecast(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = get_latest_forecast(db, product_id)
    if not result:
        raise HTTPException(status_code=404, detail="No forecast trained yet for this product")

    run = result["run"]
    history_records = [
        ForecastPointOut(date=row["date"], actual_value=row["quantity"])
        for _, row in result["history"].iterrows()
    ]
    forecast_records = [ForecastPointOut.model_validate(p) for p in result["forecast_points"]]

    metrics = ModelMetrics(
        model_type=run.model_type,
        mae=run.mae,
        rmse=run.rmse,
        mape=run.mape,
        training_time_ms=run.training_time_ms,
        is_best=run.is_best,
        feature_importance=run.feature_importance,
        forecast_run_id=run.id,
    )

    return ForecastSeriesResponse(
        product_id=product_id,
        product_name=product.name,
        forecast_run_id=run.id,
        model_type=run.model_type,
        horizon_days=run.horizon_days,
        metrics=metrics,
        history=history_records,
        forecast=forecast_records,
    )
