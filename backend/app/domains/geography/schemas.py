"""
Analytica — Geography Pydantic Schemas
"""

from pydantic import BaseModel
from app.shared.schemas import KPICard, Insight


class StateMetric(BaseModel):
    state_code: str
    total_revenue: float
    total_orders: int
    total_customers: int
    total_freight_cost: float
    revenue_share_pct: float = 0.0


class GeographyResponse(BaseModel):
    """Aggregated geography analytics response."""
    kpis: dict[str, KPICard]
    states: list[StateMetric]
    top_states: list[StateMetric]
    insights: list[Insight]
