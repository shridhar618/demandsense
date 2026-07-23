"""
Inventory Intelligence.

Computes catalog-wide inventory analytics from demand history + current
inventory snapshots. Unlike the Decision Intelligence engine (one product's
reorder decision), this operates across the whole catalog to answer
"where should I focus attention" questions.

  ABC classification  - Pareto analysis on trailing-12-month revenue
                        contribution per product. A = top 80% cumulative
                        revenue, B = next 15%, C = remaining 5%. Standard
                        inventory-management convention.
  Movement class      - turnover ratio = annualized demand / on-hand qty.
                        fast (>=12 turns/yr), medium (3-12), slow (<3).
  Dead stock          - on-hand > 0 but zero demand in the trailing window
                        (default 30 days).
  Stockout risk       - days of cover (on-hand / recent avg daily demand)
                        below the product's supplier lead time.
  Overstock           - days of cover more than 3x the lead time.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import DemandRecord, InventorySnapshot, Product

DEAD_STOCK_WINDOW_DAYS = 30
RECENT_DEMAND_WINDOW_DAYS = 14


def _classify_movement(turnover_ratio: float) -> str:
    if turnover_ratio >= 12:
        return "fast"
    if turnover_ratio >= 3:
        return "medium"
    return "slow"


def compute_inventory_intelligence(db: Session) -> dict:
    products = db.query(Product).filter(Product.is_active == True).all()  # noqa: E712
    if not products:
        return {"products": [], "summary": _empty_summary()}

    today = db.query(DemandRecord.date).order_by(DemandRecord.date.desc()).first()
    as_of = today[0] if today else date.today()
    dead_stock_cutoff = as_of - timedelta(days=DEAD_STOCK_WINDOW_DAYS)
    recent_cutoff = as_of - timedelta(days=RECENT_DEMAND_WINDOW_DAYS)

    rows = []
    for product in products:
        inventory = (
            db.query(InventorySnapshot).filter(InventorySnapshot.product_id == product.id).first()
        )
        demand_rows = (
            db.query(DemandRecord.date, DemandRecord.quantity, DemandRecord.revenue)
            .filter(DemandRecord.product_id == product.id)
            .all()
        )
        if not demand_rows:
            continue

        df = pd.DataFrame(demand_rows, columns=["date", "quantity", "revenue"])
        daily = df.groupby("date").agg(quantity=("quantity", "sum"), revenue=("revenue", "sum"))

        trailing_revenue = float(daily["revenue"].fillna(0).sum())
        trailing_quantity = float(daily["quantity"].sum())
        history_days = (daily.index.max() - daily.index.min()).days + 1 if len(daily) > 1 else 1
        annualized_demand = trailing_quantity * (365 / max(history_days, 1))

        recent_demand = float(daily.loc[daily.index > recent_cutoff, "quantity"].sum())
        recent_days = min(RECENT_DEMAND_WINDOW_DAYS, history_days)
        recent_avg_daily = recent_demand / recent_days if recent_days > 0 else 0.0

        on_hand = inventory.on_hand_quantity if inventory else 0.0
        unit_cost = inventory.unit_cost if inventory else 0.0
        lead_time = inventory.lead_time_days if inventory else 7

        turnover_ratio = (annualized_demand / on_hand) if on_hand > 0 else 0.0
        movement_class = _classify_movement(turnover_ratio) if inventory else "unknown"

        last_demand_date = daily.index.max()
        is_dead_stock = bool(inventory and on_hand > 0 and last_demand_date < dead_stock_cutoff)

        days_of_cover = (on_hand / recent_avg_daily) if recent_avg_daily > 0 else float("inf")
        stockout_risk = bool(inventory and days_of_cover < lead_time)
        overstock = bool(inventory and days_of_cover != float("inf") and days_of_cover > lead_time * 3)

        rows.append(
            {
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "trailing_revenue": round(trailing_revenue, 2),
                "trailing_quantity": round(trailing_quantity, 1),
                "on_hand_quantity": on_hand,
                "inventory_value": round(on_hand * unit_cost, 2),
                "turnover_ratio": round(turnover_ratio, 2),
                "movement_class": movement_class,
                "is_dead_stock": is_dead_stock,
                "days_of_cover": round(days_of_cover, 1) if days_of_cover != float("inf") else None,
                "stockout_risk": stockout_risk,
                "overstock": overstock,
                "has_inventory_data": inventory is not None,
            }
        )

    # ABC classification by trailing revenue (Pareto)
    rows.sort(key=lambda r: r["trailing_revenue"], reverse=True)
    total_revenue = sum(r["trailing_revenue"] for r in rows) or 1.0
    cumulative = 0.0
    for r in rows:
        cumulative += r["trailing_revenue"]
        cum_pct = cumulative / total_revenue
        if cum_pct <= 0.80:
            r["abc_class"] = "A"
        elif cum_pct <= 0.95:
            r["abc_class"] = "B"
        else:
            r["abc_class"] = "C"

    summary = {
        "total_products": len(rows),
        "total_inventory_value": round(sum(r["inventory_value"] for r in rows), 2),
        "dead_stock_count": sum(1 for r in rows if r["is_dead_stock"]),
        "stockout_risk_count": sum(1 for r in rows if r["stockout_risk"]),
        "overstock_count": sum(1 for r in rows if r["overstock"]),
        "abc_breakdown": {
            "A": sum(1 for r in rows if r["abc_class"] == "A"),
            "B": sum(1 for r in rows if r["abc_class"] == "B"),
            "C": sum(1 for r in rows if r["abc_class"] == "C"),
        },
        "movement_breakdown": {
            "fast": sum(1 for r in rows if r["movement_class"] == "fast"),
            "medium": sum(1 for r in rows if r["movement_class"] == "medium"),
            "slow": sum(1 for r in rows if r["movement_class"] == "slow"),
            "unknown": sum(1 for r in rows if r["movement_class"] == "unknown"),
        },
        "as_of": as_of.isoformat(),
    }

    return {"products": rows, "summary": summary}


def _empty_summary() -> dict:
    return {
        "total_products": 0,
        "total_inventory_value": 0,
        "dead_stock_count": 0,
        "stockout_risk_count": 0,
        "overstock_count": 0,
        "abc_breakdown": {"A": 0, "B": 0, "C": 0},
        "movement_breakdown": {"fast": 0, "medium": 0, "slow": 0, "unknown": 0},
        "as_of": None,
    }
