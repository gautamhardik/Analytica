"""
Analytica — Executive Pydantic Schemas
Response models for the executive dashboard endpoint.
"""

from pydantic import BaseModel
from app.shared.schemas import KPICard, Insight


class CustomerSnapshot(BaseModel):
    """Repeat vs one-time customer breakdown."""
    repeat_customers: int = 0
    one_time_customers: int = 0
    total_customers: int = 0
    repeat_pct: float = 0.0


class CategorySummary(BaseModel):
    """Category performance summary for top-N display."""
    product_category: str
    total_revenue: float
    total_orders: int
    total_items_sold: int
    average_item_price: float
    revenue_share_pct: float = 0.0


class StateSummary(BaseModel):
    """State performance summary for top-N display."""
    state_code: str
    total_revenue: float
    total_orders: int
    total_customers: int
    total_freight_cost: float


class MonthlyDataPoint(BaseModel):
    """Single month data point for trend charts."""
    order_month: str
    total_revenue: float
    total_orders: int
    total_customers: int
    average_order_value: float


class ExecutiveResponse(BaseModel):
    """Aggregated executive dashboard response — one request, all data."""
    kpis: dict[str, KPICard]
    monthly_trend: list[MonthlyDataPoint]
    top_categories: list[CategorySummary]
    top_states: list[StateSummary]
    customer_snapshot: CustomerSnapshot
    insights: list[Insight]
