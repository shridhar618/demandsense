from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    row: Optional[int] = None
    column: Optional[str] = None
    issue: str


class DatasetProfile(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    status: str
    row_count: int
    rejected_row_count: int
    date_range_start: Optional[date]
    date_range_end: Optional[date]
    validation_report: dict[str, Any]

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str]
    record_count: int = 0

    class Config:
        from_attributes = True


class TrainForecastRequest(BaseModel):
    product_id: int
    horizon_days: int = 30


class ModelMetrics(BaseModel):
    model_type: str
    mae: Optional[float]
    rmse: Optional[float]
    mape: Optional[float]
    training_time_ms: Optional[int]
    is_best: bool
    feature_importance: Optional[dict[str, float]] = None
    forecast_run_id: int


class TrainForecastResponse(BaseModel):
    product_id: int
    comparison_batch_id: str
    models: list[ModelMetrics]
    best_model: str


class ForecastPointOut(BaseModel):
    date: date
    predicted_value: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    actual_value: Optional[float] = None

    class Config:
        from_attributes = True


class ForecastSeriesResponse(BaseModel):
    product_id: int
    product_name: str
    forecast_run_id: int
    model_type: str
    horizon_days: int
    metrics: ModelMetrics
    history: list[ForecastPointOut]
    forecast: list[ForecastPointOut]


class InventoryUploadResponse(BaseModel):
    status: str
    row_count: int = 0
    rejected_row_count: int = 0
    validation_report: dict[str, Any] = {}
    error: Optional[str] = None


class InventorySnapshotOut(BaseModel):
    product_id: int
    warehouse: str
    on_hand_quantity: float
    unit_cost: float
    lead_time_days: int
    order_cost: float
    holding_cost_pct: float

    class Config:
        from_attributes = True


class RecommendationOut(BaseModel):
    id: int
    product_id: int
    forecast_run_id: int
    created_at: datetime
    action: str
    reason: str
    confidence: float
    priority: str
    risk: str
    business_impact: str
    estimated_savings: Optional[float]
    forecasted_demand_leadtime: Optional[float]
    safety_stock: Optional[float]
    reorder_point: Optional[float]
    economic_order_qty: Optional[float]
    days_of_cover: Optional[float]
    recommended_order_qty: Optional[float]

    class Config:
        from_attributes = True


class InventoryIntelligenceProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    category: Optional[str]
    trailing_revenue: float
    trailing_quantity: float
    on_hand_quantity: float
    inventory_value: float
    turnover_ratio: float
    movement_class: str
    is_dead_stock: bool
    days_of_cover: Optional[float]
    stockout_risk: bool
    overstock: bool
    has_inventory_data: bool
    abc_class: str


class InventoryIntelligenceSummary(BaseModel):
    total_products: int
    total_inventory_value: float
    dead_stock_count: int
    stockout_risk_count: int
    overstock_count: int
    abc_breakdown: dict[str, int]
    movement_breakdown: dict[str, int]
    as_of: Optional[str]


class InventoryIntelligenceResponse(BaseModel):
    products: list[InventoryIntelligenceProduct]
    summary: InventoryIntelligenceSummary
