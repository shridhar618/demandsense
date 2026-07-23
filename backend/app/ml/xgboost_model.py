import time

import numpy as np
import pandas as pd
import xgboost as xgb

from app.ml.metrics import compute_metrics

LAGS = [1, 7, 14, 28]
ROLLING_WINDOWS = [7, 14]


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calendar + lag + rolling-mean features. df has columns ['date','quantity']."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["day_of_week"] = out["date"].dt.dayofweek
    out["day_of_month"] = out["date"].dt.day
    out["month"] = out["date"].dt.month
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    out["week_of_year"] = out["date"].dt.isocalendar().week.astype(int)

    for lag in LAGS:
        out[f"lag_{lag}"] = out["quantity"].shift(lag)
    for window in ROLLING_WINDOWS:
        out[f"rolling_mean_{window}"] = out["quantity"].shift(1).rolling(window).mean()

    return out


FEATURE_COLUMNS = (
    ["day_of_week", "day_of_month", "month", "is_weekend", "week_of_year"]
    + [f"lag_{lag}" for lag in LAGS]
    + [f"rolling_mean_{w}" for w in ROLLING_WINDOWS]
)


def run_xgboost(history_df: pd.DataFrame, horizon_days: int, holdout_days: int) -> dict:
    """
    history_df: columns ['date', 'quantity'], daily frequency, sorted ascending.
    Uses recursive multi-step forecasting: each future day's lag features are
    filled in from the model's own prior predictions.
    """
    start = time.time()

    featured = _build_features(history_df)
    modelable = featured.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)

    eval_metrics = {"mae": None, "rmse": None, "mape": None}
    feature_importance = None

    if len(modelable) > holdout_days + 10 and holdout_days > 0:
        train = modelable.iloc[: len(modelable) - holdout_days]
        holdout = modelable.iloc[len(modelable) - holdout_days :]

        eval_model = xgb.XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9
        )
        eval_model.fit(train[FEATURE_COLUMNS], train["quantity"])
        preds = eval_model.predict(holdout[FEATURE_COLUMNS])
        eval_metrics = compute_metrics(holdout["quantity"].values, preds)

    # Final model on all available modelable rows
    final_model = xgb.XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9
    )
    final_model.fit(modelable[FEATURE_COLUMNS], modelable["quantity"])
    feature_importance = {
        col: round(float(imp), 4)
        for col, imp in zip(FEATURE_COLUMNS, final_model.feature_importances_)
    }

    # Recursive forecasting into the future
    history_series = history_df.set_index(pd.to_datetime(history_df["date"]))["quantity"].copy()
    last_date = history_series.index.max()
    forecast_rows = []

    working_series = history_series.copy()
    for step in range(1, horizon_days + 1):
        next_date = last_date + pd.Timedelta(days=step)
        feat_row = {
            "day_of_week": next_date.dayofweek,
            "day_of_month": next_date.day,
            "month": next_date.month,
            "is_weekend": int(next_date.dayofweek >= 5),
            "week_of_year": int(next_date.isocalendar()[1]),
        }
        for lag in LAGS:
            lag_date = next_date - pd.Timedelta(days=lag)
            feat_row[f"lag_{lag}"] = working_series.get(lag_date, working_series.iloc[-1])
        for window in ROLLING_WINDOWS:
            feat_row[f"rolling_mean_{window}"] = working_series.tail(window).mean()

        x = pd.DataFrame([feat_row])[FEATURE_COLUMNS]
        pred = max(0.0, float(final_model.predict(x)[0]))
        working_series.loc[next_date] = pred

        # Simple uncertainty band widening with horizon distance, anchored to
        # residual std from training as a first-order approximation
        residual_std = float(np.std(modelable["quantity"] - final_model.predict(modelable[FEATURE_COLUMNS])))
        spread = residual_std * (1 + step / horizon_days)

        forecast_rows.append(
            {
                "date": next_date.date(),
                "predicted_value": pred,
                "lower_bound": max(0.0, pred - spread),
                "upper_bound": pred + spread,
            }
        )

    training_time_ms = int((time.time() - start) * 1000)

    return {
        "model_type": "xgboost",
        "metrics": eval_metrics,
        "training_time_ms": training_time_ms,
        "feature_importance": feature_importance,
        "forecast": forecast_rows,
    }
