"""
Analytica — Sales Service
Business logic for revenue analytics, category breakdown, and trend analysis.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.schemas import KPICard
from app.shared.utils import format_currency, format_number, calc_growth_pct, determine_trend, safe_float, safe_int
from app.domains.sales import repository
from app.domains.sales.schemas import SalesResponse, MonthlySales, CategoryPerformance, StateSales
from app.domains.insights.engine import generate_sales_insights


from app.core.cache import get_cache, set_cache, make_cache_key


async def get_sales_analytics(session: AsyncSession, **filters) -> SalesResponse:
    """Assemble complete sales workspace data."""
    cache_key = make_cache_key("sales_analytics", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res
    
    kpis_data = await repository.get_sales_kpis(session, **filters)
    monthly_trend = await repository.get_monthly_revenue_trend(session, **filters)
    top_categories = await repository.get_category_performance(session, limit=8, **filters)
    sales_by_state = await repository.get_sales_by_state(session, limit=6, **filters)

    total_revenue = safe_float(kpis_data.get("total_revenue"))
    total_orders = safe_int(kpis_data.get("total_orders"))
    aov = safe_float(kpis_data.get("average_order_value"))

    # MoM growth — skip last month if incomplete (near-zero revenue)
    revenue_growth = None
    if len(monthly_trend) >= 2:
        if safe_float(monthly_trend[-1].get("total_revenue")) < 1000 and len(monthly_trend) >= 3:
            curr = monthly_trend[-2]
            prev = monthly_trend[-3]
        else:
            curr = monthly_trend[-1]
            prev = monthly_trend[-2]
        revenue_growth = calc_growth_pct(
            safe_float(curr.get("total_revenue")),
            safe_float(prev.get("total_revenue")),
        )

    kpis = {
        "total_revenue": KPICard(
            label="Total Revenue",
            value=total_revenue,
            formatted=format_currency(total_revenue),
            change_pct=revenue_growth,
            trend=determine_trend(revenue_growth),
        ),
        "total_orders": KPICard(
            label="Total Orders",
            value=float(total_orders),
            formatted=format_number(total_orders),
        ),
        "average_order_value": KPICard(
            label="AOV",
            value=aov,
            formatted=format_currency(aov),
        ),
    }

    # Monthly trend
    trend = [
        MonthlySales(
            order_month=str(m.get("order_month", "")),
            total_revenue=safe_float(m.get("total_revenue")),
            total_orders=safe_int(m.get("total_orders")),
            average_order_value=safe_float(m.get("average_order_value")),
        )
        for m in monthly_trend
    ]

    # Categories with revenue share
    categories = []
    for c in top_categories:
        rev = safe_float(c.get("total_revenue"))
        share = (rev / total_revenue * 100) if total_revenue > 0 else 0.0
        categories.append(CategoryPerformance(
            product_category=str(c.get("product_category", "")),
            total_revenue=rev,
            total_orders=safe_int(c.get("total_orders")),
            total_items_sold=safe_int(c.get("total_items_sold")),
            average_item_price=safe_float(c.get("average_item_price")),
            revenue_share_pct=round(share, 2),
        ))

    top_5 = categories[:5]
    bottom_5 = categories[-5:] if len(categories) > 10 else []

    # Sales by state
    states = [
        StateSales(
            state_code=str(s.get("state_code", "")),
            total_revenue=safe_float(s.get("total_revenue")),
            total_orders=safe_int(s.get("total_orders")),
        )
        for s in sales_by_state
    ]

    # Insights
    insights = generate_sales_insights(top_categories, monthly_trend)

    response = SalesResponse(
        kpis=kpis,
        monthly_trend=trend,
        categories=categories,
        top_categories=top_5,
        bottom_categories=bottom_5,
        sales_by_state=states,
        insights=insights,
    )
    set_cache(cache_key, response, ttl_seconds=60)
    return response

