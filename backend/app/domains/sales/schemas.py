"""
Analytica — Sales Pydantic Schemas
"""

from pydantic import BaseModel
from app.shared.schemas import KPICard, Insight


class MonthlySales(BaseModel):
    order_month: str
    total_revenue: float
    total_orders: int
    average_order_value: float


class CategoryPerformance(BaseModel):
    product_category: str
    total_revenue: float
    total_orders: int
    total_items_sold: int
    average_item_price: float
    revenue_share_pct: float = 0.0


class StateSales(BaseModel):
    state_code: str
    total_revenue: float
    total_orders: int


class SalesResponse(BaseModel):
    """Aggregated sales analytics response."""
    kpis: dict[str, KPICard]
    monthly_trend: list[MonthlySales]
    categories: list[CategoryPerformance]
    top_categories: list[CategoryPerformance]
    bottom_categories: list[CategoryPerformance]
    sales_by_state: list[StateSales]
    insights: list[Insight]
