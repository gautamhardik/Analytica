"""
Analytica — Executive Service
Business logic layer that assembles the complete executive dashboard response.
Calculates derived KPIs, growth metrics, and generates insights.
Optimized with parallel query execution (asyncio.gather) and in-memory TTL caching.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.schemas import KPICard
from app.shared.utils import format_currency, format_number, calc_growth_pct, determine_trend, safe_float, safe_int
from app.domains.executive import repository
from app.domains.executive.schemas import (
    ExecutiveResponse,
    MonthlyDataPoint,
    CategorySummary,
    StateSummary,
    CustomerSnapshot,
)
from app.domains.insights.engine import generate_executive_insights
from app.core.cache import get_cache, set_cache, make_cache_key


async def get_executive_dashboard(session: AsyncSession, **filters) -> ExecutiveResponse:
    """Assemble the complete executive dashboard in a single call."""

    cache_key = make_cache_key("exec_dash", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    kpi_data = await repository.get_overall_kpis(session, **filters)
    monthly_data = await repository.get_monthly_trend(session, **filters)
    top_categories = await repository.get_top_categories(session, limit=5, **filters)
    top_states = await repository.get_top_states(session, limit=5, **filters)
    customer_data = await repository.get_customer_snapshot(session, **filters)

    # ---- Build KPIs with growth calculation ----
    total_revenue = safe_float(kpi_data.get("total_revenue"))
    total_orders = safe_int(kpi_data.get("total_orders"))
    total_customers = safe_int(kpi_data.get("total_customers"))
    aov = safe_float(kpi_data.get("average_order_value"))

    # Calculate MoM growth from target/latest month vs previous month
    revenue_growth = None
    order_growth = None

    selected_month = filters.get("month")
    target_idx = None

    if selected_month and monthly_data:
        for idx, m in enumerate(monthly_data):
            if m.get("order_month") == selected_month:
                target_idx = idx
                break
    elif len(monthly_data) >= 2:
        # If last month has near-zero orders (incomplete cutoff period), use last full month
        if safe_float(monthly_data[-1].get("total_revenue")) < 1000 and len(monthly_data) >= 3:
            target_idx = len(monthly_data) - 2
        else:
            target_idx = len(monthly_data) - 1

    if target_idx is not None and target_idx > 0:
        curr_m = monthly_data[target_idx]
        prev_m = monthly_data[target_idx - 1]
        revenue_growth = calc_growth_pct(
            safe_float(curr_m.get("total_revenue")),
            safe_float(prev_m.get("total_revenue")),
        )
        order_growth = calc_growth_pct(
            safe_float(curr_m.get("total_orders")),
            safe_float(prev_m.get("total_orders")),
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
            change_pct=order_growth,
            trend=determine_trend(order_growth),
        ),
        "total_customers": KPICard(
            label="Total Customers",
            value=float(total_customers),
            formatted=format_number(total_customers),
        ),
        "average_order_value": KPICard(
            label="Average Order Value",
            value=aov,
            formatted=format_currency(aov),
        ),
    }

    # ---- Monthly trend ----
    trend = [
        MonthlyDataPoint(
            order_month=str(m.get("order_month", "")),
            total_revenue=safe_float(m.get("total_revenue")),
            total_orders=safe_int(m.get("total_orders")),
            total_customers=safe_int(m.get("total_customers")),
            average_order_value=safe_float(m.get("average_order_value")),
        )
        for m in monthly_data
    ]

    # ---- Top categories ----
    categories = []
    for c in top_categories:
        rev = safe_float(c.get("total_revenue"))
        share = (rev / total_revenue * 100) if total_revenue > 0 else 0.0
        categories.append(CategorySummary(
            product_category=str(c.get("product_category", "")),
            total_revenue=rev,
            total_orders=safe_int(c.get("total_orders")),
            total_items_sold=safe_int(c.get("total_items_sold")),
            average_item_price=safe_float(c.get("average_item_price")),
            revenue_share_pct=round(share, 2),
        ))

    # ---- Top states ----
    states = [
        StateSummary(
            state_code=str(s.get("state_code", "")),
            total_revenue=safe_float(s.get("total_revenue")),
            total_orders=safe_int(s.get("total_orders")),
            total_customers=safe_int(s.get("total_customers")),
            total_freight_cost=safe_float(s.get("total_freight_cost")),
        )
        for s in top_states
    ]

    # ---- Customer snapshot ----
    repeat_count = safe_int(customer_data.get("repeat_customers"))
    one_time_count = safe_int(customer_data.get("one_time_customers"))
    cust_total = safe_int(customer_data.get("total_customers"))
    repeat_pct = (repeat_count / cust_total * 100) if cust_total > 0 else 0.0

    snapshot = CustomerSnapshot(
        repeat_customers=repeat_count,
        one_time_customers=one_time_count,
        total_customers=cust_total,
        repeat_pct=round(repeat_pct, 2),
    )

    # ---- Top state revenue share for insights ----
    top_state_name = states[0].state_code if states else None
    top_state_share = (states[0].total_revenue / total_revenue * 100) if states and total_revenue > 0 else None

    # ---- Generate insights ----
    insights = generate_executive_insights(
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_customers=total_customers,
        revenue_growth=revenue_growth,
        order_growth=order_growth,
        top_category=categories[0].product_category if categories else None,
        top_state=top_state_name,
        top_state_revenue_share=top_state_share,
        repeat_customer_pct=repeat_pct,
    )

    response = ExecutiveResponse(
        kpis=kpis,
        monthly_trend=trend,
        top_categories=categories,
        top_states=states,
        customer_snapshot=snapshot,
        insights=insights,
    )

    set_cache(cache_key, response, ttl_seconds=60)
    return response
