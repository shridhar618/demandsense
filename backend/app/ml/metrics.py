import numpy as np


def compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """MAE, RMSE, MAPE on a holdout set. MAPE guards against divide-by-zero."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mae = float(np.mean(np.abs(actual - predicted)))
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

    nonzero_mask = actual != 0
    if nonzero_mask.any():
        mape = float(
            np.mean(np.abs((actual[nonzero_mask] - predicted[nonzero_mask]) / actual[nonzero_mask])) * 100
        )
    else:
        mape = None

    return {"mae": round(mae, 3), "rmse": round(rmse, 3), "mape": round(mape, 3) if mape is not None else None}
