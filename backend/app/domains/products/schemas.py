"""
Analytica — Products Pydantic Schemas
"""

from pydantic import BaseModel
from app.shared.schemas import KPICard, Insight


class CategoryDetail(BaseModel):
    product_category: str
    total_revenue: float
    total_orders: int
    total_items_sold: int
    average_item_price: float
    revenue_share_pct: float = 0.0


class SellerDetail(BaseModel):
    seller_id: str
    seller_state: str | None
    seller_city: str | None
    orders_fulfilled: int
    items_sold: int
    total_revenue_generated: float


class ProductsResponse(BaseModel):
    """Aggregated products/category analytics response."""
    kpis: dict[str, KPICard]
    categories: list[CategoryDetail]
    top_categories: list[CategoryDetail]
    bottom_categories: list[CategoryDetail]
    top_sellers: list[SellerDetail]
    insights: list[Insight]
