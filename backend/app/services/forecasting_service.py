import uuid
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.prophet_model import run_prophet
from app.ml.xgboost_model import run_xgboost
from app.models.models import DemandRecord, ForecastPoint, ForecastRun, Product


class InsufficientHistoryError(Exception):
    pass


def _load_product_history(db: Session, product_id: int) -> pd.DataFrame:
    """Aggregates across warehouses into a single daily series per product."""
    rows = (
        db.query(DemandRecord.date, DemandRecord.quantity)
        .filter(DemandRecord.product_id == product_id)
        .order_by(DemandRecord.date)
        .all()
    )
    df = pd.DataFrame(rows, columns=["date", "quantity"])
    if df.empty:
        return df
    df = df.groupby("date", as_index=False)["quantity"].sum()
    return df


def train_and_compare(db: Session, product_id: int, horizon_days: int) -> dict:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product {product_id} not found")

    history_df = _load_product_history(db, product_id)
    if len(history_df) < 14:
        raise InsufficientHistoryError(
            f"Need at least 14 days of history to train, found {len(history_df)}"
        )

    holdout_days = max(7, min(14, len(history_df) // 5))
    dataset_id = (
        db.query(DemandRecord.dataset_id)
        .filter(DemandRecord.product_id == product_id)
        .order_by(DemandRecord.id.desc())
        .first()[0]
    )

    batch_id = str(uuid.uuid4())[:8]
    results = []

    for runner in (run_prophet, run_xgboost):
        result = runner(history_df, horizon_days=horizon_days, holdout_days=holdout_days)

        run = ForecastRun(
            product_id=product_id,
            dataset_id=dataset_id,
            horizon_days=horizon_days,
            model_type=result["model_type"],
            mae=result["metrics"]["mae"],
            rmse=result["metrics"]["rmse"],
            mape=result["metrics"]["mape"],
            training_time_ms=result["training_time_ms"],
            feature_importance=result["feature_importance"],
            comparison_batch_id=batch_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        points = [
            ForecastPoint(
                forecast_run_id=run.id,
                date=p["date"],
                predicted_value=p["predicted_value"],
                lower_bound=p["lower_bound"],
                upper_bound=p["upper_bound"],
            )
            for p in result["forecast"]
        ]
        db.bulk_save_objects(points)
        db.commit()

        results.append({"run": run, "metrics": result["metrics"]})

    # Determine best model by MAE (lower is better); fall back gracefully if MAE missing
    scored = [r for r in results if r["metrics"]["mae"] is not None]
    best = min(scored, key=lambda r: r["metrics"]["mae"]) if scored else results[0]
    best["run"].is_best = True
    db.commit()

    return {
        "product_id": product_id,
        "comparison_batch_id": batch_id,
        "best_model": best["run"].model_type,
        "runs": [r["run"] for r in results],
    }


def get_latest_forecast(db: Session, product_id: int) -> dict | None:
    best_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.product_id == product_id, ForecastRun.is_best == True)  # noqa: E712
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    if not best_run:
        return None

    history_df = _load_product_history(db, product_id)
    forecast_points = (
        db.query(ForecastPoint)
        .filter(ForecastPoint.forecast_run_id == best_run.id)
        .order_by(ForecastPoint.date)
        .all()
    )
    return {"run": best_run, "history": history_df, "forecast_points": forecast_points}
