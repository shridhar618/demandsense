"""
Inventory snapshot ingestion.

Unlike demand history, inventory is a *current position*, not a time series:
re-uploading replaces the prior row for that product+warehouse rather than
appending. Expected CSV columns (case-insensitive):

  product_sku          (required) - must match a product already known from a demand upload
  on_hand_quantity      (required) - current stock on hand
  warehouse              (optional) - defaults to "DEFAULT"
  unit_cost               (optional) - defaults to 0
  lead_time_days           (optional) - supplier lead time, defaults to 7
  order_cost                 (optional) - fixed cost per purchase order, defaults to 50
  holding_cost_pct             (optional) - annual holding cost as a fraction of unit cost, defaults to 0.20
"""
from __future__ import annotations

import io
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import InventorySnapshot, Product

REQUIRED_COLUMNS = {"product_sku", "on_hand_quantity"}

DEFAULTS = {
    "warehouse": "DEFAULT",
    "unit_cost": 0.0,
    "lead_time_days": 7,
    "order_cost": 50.0,
    "holding_cost_pct": 0.20,
}


def ingest_inventory_csv(db: Session, filename: str, file_bytes: bytes) -> dict[str, Any]:
    report: dict[str, Any] = {"stages": [], "issues": []}

    try:
        raw = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"Could not parse CSV: {exc}"}

    raw.columns = [c.strip().lower().replace(" ", "_") for c in raw.columns]

    missing_cols = REQUIRED_COLUMNS - set(raw.columns)
    if missing_cols:
        return {
            "status": "failed",
            "error": f"Missing required columns: {sorted(missing_cols)}",
            "required_columns": sorted(REQUIRED_COLUMNS),
        }
    report["stages"].append("schema_validation_passed")

    for col, default in DEFAULTS.items():
        if col not in raw.columns:
            raw[col] = default
        else:
            raw[col] = raw[col].fillna(default)

    raw["on_hand_quantity"] = pd.to_numeric(raw["on_hand_quantity"], errors="coerce")
    bad_mask = raw["on_hand_quantity"].isna()
    rejected = int(bad_mask.sum())
    clean = raw.loc[~bad_mask].copy()
    if rejected:
        report["issues"].append({"issue": f"{rejected} row(s) dropped: unparseable on_hand_quantity"})

    unknown_skus = []
    upserted = 0
    for _, row in clean.iterrows():
        product = db.query(Product).filter(Product.sku == row["product_sku"]).first()
        if not product:
            unknown_skus.append(row["product_sku"])
            continue

        existing = (
            db.query(InventorySnapshot)
            .filter(
                InventorySnapshot.product_id == product.id,
                InventorySnapshot.warehouse == row["warehouse"],
            )
            .first()
        )
        values = dict(
            on_hand_quantity=float(row["on_hand_quantity"]),
            unit_cost=float(row["unit_cost"]),
            lead_time_days=int(row["lead_time_days"]),
            order_cost=float(row["order_cost"]),
            holding_cost_pct=float(row["holding_cost_pct"]),
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            db.add(
                InventorySnapshot(
                    product_id=product.id, warehouse=row["warehouse"], **values
                )
            )
        upserted += 1

    if unknown_skus:
        report["issues"].append(
            {"issue": f"{len(unknown_skus)} row(s) skipped: SKU not found (upload demand history first) — {sorted(set(unknown_skus))[:5]}"}
        )

    db.commit()
    report["stages"].append("persisted")

    return {
        "status": "validated" if upserted > 0 else "failed",
        "row_count": upserted,
        "rejected_row_count": rejected + len(unknown_skus),
        "validation_report": report,
        "error": None if upserted > 0 else "No rows could be matched to known products",
    }
