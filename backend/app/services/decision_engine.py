"""
Decision Intelligence engine.

Turns "what will demand be" into "what should we do about it" using
standard inventory-management formulas, not black-box AI:

  avg_daily_demand, std_daily_demand   from historical demand_records
  safety_stock   = z * std_daily_demand * sqrt(lead_time_days)
                   (z is the service-level factor, e.g. 1.65 for ~95%)
  reorder_point  = avg_daily_demand * lead_time_days + safety_stock
  EOQ            = sqrt(2 * annual_demand * order_cost / holding_cost_per_unit)
                   (classic Economic Order Quantity / Wilson formula)
  days_of_cover  = on_hand_quantity / forecasted_daily_demand_rate

The forecasted (not just historical) daily rate is used for days-of-cover
and the "should we act" decision, since a decision should be forward-looking
-- that's the entire point of forecasting before deciding.
"""
from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import (
    DemandRecord,
    ForecastPoint,
    ForecastRun,
    InventorySnapshot,
    Product,
    Recommendation,
)


class MissingPrerequisiteError(Exception):
    pass


def _historical_demand_stats(db: Session, product_id: int) -> tuple[float, float]:
    rows = (
        db.query(DemandRecord.date, DemandRecord.quantity)
        .filter(DemandRecord.product_id == product_id)
        .all()
    )
    df = pd.DataFrame(rows, columns=["date", "quantity"])
    daily = df.groupby("date")["quantity"].sum()
    return float(daily.mean()), float(daily.std(ddof=0) or 0.0)


def _forecasted_demand_over_leadtime(db: Session, forecast_run: ForecastRun, lead_time_days: int) -> tuple[float, float]:
    """Returns (total forecasted demand over lead_time_days, implied daily rate)."""
    points = (
        db.query(ForecastPoint.predicted_value)
        .filter(ForecastPoint.forecast_run_id == forecast_run.id)
        .order_by(ForecastPoint.date)
        .limit(lead_time_days)
        .all()
    )
    values = [p[0] for p in points]
    if not values:
        return 0.0, 0.0

    # If the forecast horizon is shorter than the lead time, extrapolate
    # using the average of what we do have.
    avg_daily = sum(values) / len(values)
    if len(values) < lead_time_days:
        total = sum(values) + avg_daily * (lead_time_days - len(values))
    else:
        total = sum(values)
    return total, avg_daily


def generate_recommendation(db: Session, product_id: int) -> Recommendation:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product {product_id} not found")

    inventory = db.query(InventorySnapshot).filter(InventorySnapshot.product_id == product_id).first()
    if not inventory:
        raise MissingPrerequisiteError(
            "No inventory snapshot for this product — upload inventory levels first"
        )

    forecast_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.product_id == product_id, ForecastRun.is_best == True)  # noqa: E712
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    if not forecast_run:
        raise MissingPrerequisiteError("No trained forecast for this product — train forecasts first")

    avg_daily_demand, std_daily_demand = _historical_demand_stats(db, product_id)
    forecasted_leadtime_demand, forecasted_daily_rate = _forecasted_demand_over_leadtime(
        db, forecast_run, inventory.lead_time_days
    )

    # Blend: prefer the forward-looking forecasted rate, but never let it be
    # zero if the forecast run is degenerate -- fall back to history.
    effective_daily_rate = forecasted_daily_rate if forecasted_daily_rate > 0 else avg_daily_demand

    safety_stock = inventory.service_level_z * std_daily_demand * math.sqrt(max(inventory.lead_time_days, 1))
    reorder_point = avg_daily_demand * inventory.lead_time_days + safety_stock

    annual_demand_estimate = avg_daily_demand * 365
    holding_cost_per_unit = max(inventory.unit_cost * inventory.holding_cost_pct, 0.01)
    economic_order_qty = math.sqrt(
        max(2 * annual_demand_estimate * inventory.order_cost / holding_cost_per_unit, 0.0)
    )

    days_of_cover = (
        inventory.on_hand_quantity / effective_daily_rate if effective_daily_rate > 0 else float("inf")
    )

    # --- Decision logic ---
    action: str
    reason: str
    priority: str
    risk: str
    business_impact: str
    estimated_savings: float | None = None
    recommended_order_qty: float | None = None

    overstock_threshold = reorder_point + 2 * economic_order_qty

    if inventory.on_hand_quantity <= reorder_point:
        shortfall_vs_leadtime_demand = max(0.0, forecasted_leadtime_demand + safety_stock - inventory.on_hand_quantity)
        recommended_order_qty = round(max(economic_order_qty, shortfall_vs_leadtime_demand), 1)

        if days_of_cover < inventory.lead_time_days * 0.6:
            action = "purchase_immediately"
            priority = "critical" if days_of_cover < inventory.lead_time_days * 0.3 else "high"
            risk = "high"
            reason = (
                f"On-hand stock ({inventory.on_hand_quantity:.0f} units) covers only "
                f"{days_of_cover:.1f} days at the forecasted demand rate, but the supplier "
                f"lead time is {inventory.lead_time_days} days — a stockout is likely before "
                f"replenishment arrives."
            )
            shortfall_units = max(0.0, forecasted_leadtime_demand - inventory.on_hand_quantity)
            business_impact = (
                f"Projected shortfall of ~{shortfall_units:.0f} units against lead-time demand; "
                f"unmitigated this risks stockout and lost sales during the replenishment window."
            )
            estimated_savings = round(shortfall_units * inventory.unit_cost, 2)
        else:
            action = "increase_inventory"
            priority = "medium"
            risk = "medium"
            reason = (
                f"On-hand stock ({inventory.on_hand_quantity:.0f} units) has fallen to or below "
                f"the reorder point ({reorder_point:.0f} units, based on {inventory.lead_time_days}-day "
                f"lead time and {avg_daily_demand:.1f}/day historical demand plus safety stock)."
            )
            business_impact = (
                f"Placing an order now keeps stock above the reorder point through the lead-time "
                f"window; delaying risks crossing into stockout territory."
            )
            estimated_savings = None

    elif inventory.on_hand_quantity > overstock_threshold:
        excess_units = inventory.on_hand_quantity - overstock_threshold
        action = "reduce_inventory"
        priority = "low" if excess_units < economic_order_qty else "medium"
        risk = "low"
        reason = (
            f"On-hand stock ({inventory.on_hand_quantity:.0f} units) exceeds the reorder point "
            f"plus a full order cycle ({overstock_threshold:.0f} units) by {excess_units:.0f} units — "
            f"more than needed to cover demand through the next likely reorder."
        )
        annual_holding_cost_on_excess = excess_units * holding_cost_per_unit
        business_impact = (
            f"~{excess_units:.0f} units of excess stock are tying up working capital and "
            f"incurring holding costs unnecessarily."
        )
        estimated_savings = round(annual_holding_cost_on_excess, 2)
        recommended_order_qty = round(-excess_units, 1)

    else:
        action = "monitor"
        priority = "low"
        risk = "low"
        reason = (
            f"On-hand stock ({inventory.on_hand_quantity:.0f} units) is within the healthy range "
            f"between the reorder point ({reorder_point:.0f}) and overstock threshold "
            f"({overstock_threshold:.0f}) given forecasted demand."
        )
        business_impact = "No action needed; inventory position is aligned with forecasted demand."

    # Confidence derived from the forecasting model's own held-out accuracy (MAPE).
    # Lower MAPE -> higher confidence in the recommendation that depends on it.
    if forecast_run.mape is not None:
        confidence = max(0.5, min(0.97, 1 - (forecast_run.mape / 100)))
    else:
        confidence = 0.7

    rec = Recommendation(
        product_id=product_id,
        forecast_run_id=forecast_run.id,
        created_at=datetime.utcnow(),
        action=action,
        reason=reason,
        confidence=round(confidence, 3),
        priority=priority,
        risk=risk,
        business_impact=business_impact,
        estimated_savings=estimated_savings,
        forecasted_demand_leadtime=round(forecasted_leadtime_demand, 1),
        safety_stock=round(safety_stock, 1),
        reorder_point=round(reorder_point, 1),
        economic_order_qty=round(economic_order_qty, 1),
        days_of_cover=round(days_of_cover, 1) if days_of_cover != float("inf") else None,
        recommended_order_qty=recommended_order_qty,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_latest_recommendation(db: Session, product_id: int) -> Recommendation | None:
    return (
        db.query(Recommendation)
        .filter(Recommendation.product_id == product_id)
        .order_by(Recommendation.created_at.desc())
        .first()
    )
