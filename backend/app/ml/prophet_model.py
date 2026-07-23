import os
import time

import pandas as pd

# Ensure Prophet's CmdStanPy backend points at the fully-built CmdStan toolchain.
# The pip-installed prophet wheel ships a stripped-down bundled CmdStan directory
# (stan_model/cmdstan-<version>) that has no Makefile and fails cmdstanpy's
# validation; setting CMDSTAN to a complete toolchain (built via
# `python -m cmdstanpy.install_cmdstan`) avoids that broken path being used.
os.environ.setdefault("CMDSTAN", os.path.expanduser("~/.cmdstan/cmdstan-2.39.0"))

from prophet import Prophet  # noqa: E402

from app.ml.metrics import compute_metrics  # noqa: E402


def run_prophet(history_df: pd.DataFrame, horizon_days: int, holdout_days: int) -> dict:
    """
    history_df: columns ['date', 'quantity'], daily frequency, sorted ascending.
    Trains on all-but-holdout, evaluates on holdout, then retrains on full
    history to produce the true future forecast.
    """
    start = time.time()

    df = history_df.rename(columns={"date": "ds", "quantity": "y"}).copy()
    df["ds"] = pd.to_datetime(df["ds"])

    train_df = df.iloc[: len(df) - holdout_days] if holdout_days > 0 else df
    holdout_df = df.iloc[len(df) - holdout_days :] if holdout_days > 0 else df.iloc[0:0]

    eval_metrics = {"mae": None, "rmse": None, "mape": None}
    if not holdout_df.empty and len(train_df) >= 10:
        eval_model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
        eval_model.fit(train_df)
        eval_future = eval_model.make_future_dataframe(periods=len(holdout_df), freq="D")
        eval_forecast = eval_model.predict(eval_future)
        predicted_holdout = eval_forecast.tail(len(holdout_df))["yhat"].values
        eval_metrics = compute_metrics(holdout_df["y"].values, predicted_holdout)

    # Final model trained on full history for the actual future forecast
    final_model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    final_model.fit(df)
    future = final_model.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = final_model.predict(future)

    future_only = forecast.tail(horizon_days)
    training_time_ms = int((time.time() - start) * 1000)

    return {
        "model_type": "prophet",
        "metrics": eval_metrics,
        "training_time_ms": training_time_ms,
        "feature_importance": None,
        "forecast": [
            {
                "date": row["ds"].date(),
                "predicted_value": max(0.0, float(row["yhat"])),
                "lower_bound": max(0.0, float(row["yhat_lower"])),
                "upper_bound": max(0.0, float(row["yhat_upper"])),
            }
            for _, row in future_only.iterrows()
        ],
    }
