"""
Core schema for the ingestion + forecasting slice.

Design notes:
- `datasets` is an audit/versioning table: every upload is tracked with its
  validation report, so we always know which raw file produced which
  demand_records and which forecast runs trained on them.
- `demand_records` is the cleaned, normalized time series -- one row per
  (product, warehouse, date). A unique constraint prevents duplicate rows
  from re-uploads (idempotent ingestion).
- `forecast_runs` / `forecast_points` are versioned: a product can have many
  runs over time (different models, retrains), and the UI always asks for
  "latest" or a specific run_id, never assumes a single current forecast.
- Soft deletes (`is_active`) are used instead of hard deletes to preserve
  audit history, per the project's data-governance requirements.
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="processing")  # processing | validated | failed
    row_count = Column(Integer, default=0)
    rejected_row_count = Column(Integer, default=0)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    validation_report = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    records = relationship("DemandRecord", back_populates="dataset")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True, default="Uncategorized")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    records = relationship("DemandRecord", back_populates="product")
    forecast_runs = relationship("ForecastRun", back_populates="product")


class DemandRecord(Base):
    __tablename__ = "demand_records"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse", "date", name="uq_product_warehouse_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    warehouse = Column(String, nullable=False, default="DEFAULT")
    date = Column(Date, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    revenue = Column(Float, nullable=True)
    is_imputed = Column(Boolean, default=False)  # true if filled during cleaning

    product = relationship("Product", back_populates="records")
    dataset = relationship("Dataset", back_populates="records")


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    horizon_days = Column(Integer, nullable=False)
    model_type = Column(String, nullable=False)  # prophet | xgboost
    is_best = Column(Boolean, default=False)  # best of the comparison set for this batch
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    training_time_ms = Column(Integer, nullable=True)
    feature_importance = Column(JSON, nullable=True)  # null for prophet
    comparison_batch_id = Column(String, index=True)  # ties prophet+xgboost runs together

    product = relationship("Product", back_populates="forecast_runs")
    points = relationship("ForecastPoint", back_populates="run")


class ForecastPoint(Base):
    __tablename__ = "forecast_points"

    id = Column(Integer, primary_key=True, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id"), nullable=False)
    date = Column(Date, nullable=False)
    predicted_value = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)  # backfilled for holdout evaluation points

    run = relationship("ForecastRun", back_populates="points")


class InventorySnapshot(Base):
    """
    Current on-hand position for a product. Uploaded as a CSV snapshot (not a
    time series like demand) -- re-uploading replaces the prior snapshot for
    that product+warehouse, since only the current position matters for
    reorder decisions.
    """
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse", name="uq_inventory_product_warehouse"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse = Column(String, nullable=False, default="DEFAULT")
    on_hand_quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, nullable=False, default=7)
    order_cost = Column(Float, nullable=False, default=50.0)  # fixed cost per purchase order
    holding_cost_pct = Column(Float, nullable=False, default=0.20)  # annual holding cost as % of unit cost
    service_level_z = Column(Float, nullable=False, default=1.65)  # z-score for ~95% service level
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product")


class Recommendation(Base):
    """
    A generated decision: what action to take on a product's inventory
    position, and why. Versioned like forecasts -- every generation run is
    kept, not overwritten, so recommendation history is auditable.
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    action = Column(String, nullable=False)  # increase_inventory | reduce_inventory | purchase_immediately | monitor
    reason = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)  # 0-1
    priority = Column(String, nullable=False)  # low | medium | high | critical
    risk = Column(String, nullable=False)  # low | medium | high
    business_impact = Column(String, nullable=False)
    estimated_savings = Column(Float, nullable=True)

    # Supporting calculations, kept for transparency/auditability
    forecasted_demand_leadtime = Column(Float, nullable=True)
    safety_stock = Column(Float, nullable=True)
    reorder_point = Column(Float, nullable=True)
    economic_order_qty = Column(Float, nullable=True)
    days_of_cover = Column(Float, nullable=True)
    recommended_order_qty = Column(Float, nullable=True)

    product = relationship("Product")
    forecast_run = relationship("ForecastRun")
