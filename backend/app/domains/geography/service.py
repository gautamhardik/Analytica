"""
Analytica — Geography Service
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.schemas import KPICard
from app.shared.utils import format_currency, format_number, safe_float, safe_int
from app.domains.geography import repository
from app.domains.geography.schemas import GeographyResponse, StateMetric
from app.domains.insights.engine import generate_geography_insights


import asyncio
from app.core.cache import get_cache, set_cache, make_cache_key


async def get_geography_analytics(session: AsyncSession, **filters) -> GeographyResponse:
    """Assemble the complete geography analytics response."""
    cache_key = make_cache_key("geography_analytics", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    states_data = await repository.get_all_states(session, **filters)
    totals = await repository.get_state_totals(session, **filters)

    total_revenue = safe_float(totals.get("total_revenue"))
    total_orders = safe_int(totals.get("total_orders"))
    total_states = safe_int(totals.get("total_states"))
    total_freight = safe_float(totals.get("total_freight"))

    kpis = {
        "total_states": KPICard(
            label="Active States", value=float(total_states),
            formatted=format_number(total_states),
        ),
        "total_revenue": KPICard(
            label="Total Revenue", value=total_revenue,
            formatted=format_currency(total_revenue),
        ),
        "total_freight": KPICard(
            label="Total Freight", value=total_freight,
            formatted=format_currency(total_freight),
        ),
    }

    states = []
    for s in states_data:
        rev = safe_float(s.get("total_revenue"))
        share = (rev / total_revenue * 100) if total_revenue > 0 else 0.0
        states.append(StateMetric(
            state_code=str(s.get("state_code", "")),
            total_revenue=rev,
            total_orders=safe_int(s.get("total_orders")),
            total_customers=safe_int(s.get("total_customers")),
            total_freight_cost=safe_float(s.get("total_freight_cost")),
            revenue_share_pct=round(share, 2),
        ))

    insights = generate_geography_insights(states_data, total_revenue)

    response = GeographyResponse(
        kpis=kpis, states=states, top_states=states[:10], insights=insights,
    )
    set_cache(cache_key, response, ttl_seconds=60)
    return response

