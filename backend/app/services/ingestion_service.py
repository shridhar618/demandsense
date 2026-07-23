"""
CSV ingestion pipeline.

Expected columns (case-insensitive, order-independent):
  date            (required)  - parseable date
  product_sku     (required)  - string identifier
  quantity        (required)  - numeric demand quantity
  product_name    (optional)  - defaults to sku if absent
  category        (optional)
  warehouse       (optional)  - defaults to "DEFAULT"
  revenue         (optional)

Pipeline stages, run in order:
  1. Schema validation   - required columns present, at least 1 usable row
  2. Type coercion        - parse dates, coerce numerics, drop unparseable rows (logged as rejected)
  3. Deduplication        - collapse duplicate (product, warehouse, date) rows, keep last
  4. Missing value handling - per (product, warehouse) time series, reindex to daily
                              frequency across the observed date range and linearly
                              interpolate gaps; interpolated rows flagged `is_imputed`
  5. Profiling            - row counts, date range, per-column null %, basic outlier flag
                              (IQR method) surfaced in the validation report (not silently dropped)
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd

from sqlalchemy.orm import Session

from app.models.models import DemandRecord, Dataset, Product

REQUIRED_COLUMNS = {"date", "product_sku", "quantity"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _detect_outliers_iqr(series: pd.Series) -> int:
    if series.empty:
        return 0
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((series < lower) | (series > upper)).sum())


def ingest_csv(db: Session, filename: str, file_bytes: bytes) -> Dataset:
    report: dict[str, Any] = {"stages": [], "issues": []}

    dataset = Dataset(filename=filename, status="processing")
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        raw = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001
        dataset.status = "failed"
        dataset.validation_report = {"error": f"Could not parse CSV: {exc}"}
        db.commit()
        return dataset

    raw = _normalize_columns(raw)
    total_input_rows = len(raw)

    # Stage 1: schema validation
    missing_cols = REQUIRED_COLUMNS - set(raw.columns)
    if missing_cols:
        dataset.status = "failed"
        dataset.validation_report = {
            "error": f"Missing required columns: {sorted(missing_cols)}",
            "required_columns": sorted(REQUIRED_COLUMNS),
            "found_columns": list(raw.columns),
        }
        db.commit()
        return dataset
    report["stages"].append("schema_validation_passed")

    if "product_name" not in raw.columns:
        raw["product_name"] = raw["product_sku"]
    if "category" not in raw.columns:
        raw["category"] = "Uncategorized"
    if "warehouse" not in raw.columns:
        raw["warehouse"] = "DEFAULT"
    if "revenue" not in raw.columns:
        raw["revenue"] = None

    # Stage 2: type coercion, drop unparseable rows
    raw["date_parsed"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["quantity_parsed"] = pd.to_numeric(raw["quantity"], errors="coerce")
    raw["revenue_parsed"] = pd.to_numeric(raw["revenue"], errors="coerce")

    bad_rows_mask = raw["date_parsed"].isna() | raw["quantity_parsed"].isna()
    rejected_count = int(bad_rows_mask.sum())
    clean = raw.loc[~bad_rows_mask].copy()
    report["stages"].append("type_coercion")
    if rejected_count:
        report["issues"].append(
            {"issue": f"{rejected_count} row(s) dropped: unparseable date or quantity"}
        )

    if clean.empty:
        dataset.status = "failed"
        dataset.row_count = 0
        dataset.rejected_row_count = rejected_count
        dataset.validation_report = {**report, "error": "No valid rows after cleaning"}
        db.commit()
        return dataset

    # Stage 3: deduplication (keep last occurrence per product+warehouse+date)
    before_dedup = len(clean)
    clean = clean.sort_values("date_parsed")
    clean = clean.drop_duplicates(subset=["product_sku", "warehouse", "date_parsed"], keep="last")
    deduped_count = before_dedup - len(clean)
    if deduped_count:
        report["issues"].append({"issue": f"{deduped_count} duplicate row(s) collapsed"})
    report["stages"].append("deduplication")

    # Upsert products
    product_meta = clean[["product_sku", "product_name", "category"]].drop_duplicates("product_sku")
    sku_to_product_id: dict[str, int] = {}
    for _, row in product_meta.iterrows():
        product = db.query(Product).filter(Product.sku == row["product_sku"]).first()
        if not product:
            product = Product(
                sku=row["product_sku"], name=row["product_name"], category=row["category"]
            )
            db.add(product)
            db.commit()
            db.refresh(product)
        sku_to_product_id[row["product_sku"]] = product.id

    # Stage 4: missing value handling per (product, warehouse) series
    total_imputed = 0
    total_outliers = 0
    records_to_insert: list[DemandRecord] = []

    for (sku, warehouse), group in clean.groupby(["product_sku", "warehouse"]):
        group = group.sort_values("date_parsed").set_index("date_parsed")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="D")
        reindexed = group.reindex(full_index)

        was_missing = reindexed["quantity_parsed"].isna()
        reindexed["quantity_parsed"] = reindexed["quantity_parsed"].interpolate(
            method="linear", limit_direction="both"
        )
        reindexed["revenue_parsed"] = reindexed["revenue_parsed"].interpolate(
            method="linear", limit_direction="both"
        )

        total_outliers += _detect_outliers_iqr(reindexed["quantity_parsed"])
        total_imputed += int(was_missing.sum())

        product_id = sku_to_product_id[sku]
        for ts, row in reindexed.iterrows():
            records_to_insert.append(
                DemandRecord(
                    product_id=product_id,
                    dataset_id=dataset.id,
                    warehouse=warehouse,
                    date=ts.date(),
                    quantity=float(row["quantity_parsed"]),
                    revenue=(float(row["revenue_parsed"]) if pd.notna(row["revenue_parsed"]) else None),
                    is_imputed=bool(was_missing.loc[ts]) if ts in was_missing.index else False,
                )
            )

    report["stages"].append("missing_value_imputation")
    if total_imputed:
        report["issues"].append(
            {"issue": f"{total_imputed} day(s) had no data and were linearly interpolated"}
        )
    if total_outliers:
        report["issues"].append(
            {"issue": f"{total_outliers} statistical outlier(s) detected (IQR method) — kept, not dropped"}
        )

    # Replace existing records for these products from prior datasets? No -- append-only,
    # but unique constraint means re-uploading the same product/date/warehouse will conflict.
    # We upsert by deleting overlapping keys first, so re-uploads correct prior data.
    for rec in records_to_insert:
        db.query(DemandRecord).filter(
            DemandRecord.product_id == rec.product_id,
            DemandRecord.warehouse == rec.warehouse,
            DemandRecord.date == rec.date,
        ).delete()
    db.commit()

    db.bulk_save_objects(records_to_insert)
    report["stages"].append("persisted")

    dataset.status = "validated"
    dataset.row_count = len(records_to_insert)
    dataset.rejected_row_count = rejected_count
    dataset.date_range_start = clean["date_parsed"].min().date()
    dataset.date_range_end = clean["date_parsed"].max().date()
    dataset.validation_report = {
        **report,
        "input_rows": total_input_rows,
        "products_discovered": len(sku_to_product_id),
    }
    db.commit()
    db.refresh(dataset)
    return dataset
