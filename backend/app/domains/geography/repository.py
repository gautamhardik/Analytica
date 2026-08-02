"""
Analytica — Geography Repository
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.query_builder import (
    build_dimensional_query,
    build_exec_cube_where,
    can_use_exec_cube,
    has_active_filters,
)

HAS_FILTERS = {"month", "state", "category", "segment", "seller"}
GEOGRAPHY_IGNORE_FILTERS = {"state"}  # state filter on geography page is circular


def _any_filter(filters: dict) -> bool:
    return has_active_filters(filters, HAS_FILTERS - GEOGRAPHY_IGNORE_FILTERS)


async def get_all_states(session: AsyncSession, **filters) -> list[dict]:
    """Fetch all state-level metrics."""
    geo_filters = {k: v for k, v in filters.items() if k != "state"}
    if not _any_filter(geo_filters):
        result = await session.execute(text("""
            SELECT
                state_code,
                total_revenue,
                total_orders,
                total_customers,
                total_freight_cost
            FROM reporting_state_summary
            ORDER BY total_revenue DESC
        """))
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(geo_filters):
        where, params = build_exec_cube_where(geo_filters)
        result = await session.execute(text(f"""
            SELECT
                state_code,
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                COUNT(DISTINCT customer_unique_id) AS total_customers,
                COALESCE(SUM(freight), 0) AS total_freight_cost
            FROM rpt_exec_orders{where}
            GROUP BY state_code
            ORDER BY total_revenue DESC
        """), params)
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            dg.state_code,
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            SUM(fs.freight_value) AS total_freight_cost
        """,
        group_by="dg.state_code",
        order_by="total_revenue DESC",
        **geo_filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_state_totals(session: AsyncSession, **filters) -> dict:
    """Aggregate totals across all states."""
    geo_filters = {k: v for k, v in filters.items() if k != "state"}
    if not _any_filter(geo_filters):
        result = await session.execute(text("""
            SELECT
                SUM(total_revenue) AS total_revenue,
                SUM(total_orders) AS total_orders,
                (SELECT COUNT(*) FROM reporting_filter_customer_orders) AS total_customers,
                SUM(total_freight_cost) AS total_freight,
                COUNT(*) AS total_states
            FROM reporting_state_summary
        """))
        row = result.mappings().first()
        return dict(row) if row else {"total_revenue": 0, "total_orders": 0, "total_customers": 0, "total_freight": 0, "total_states": 0}

    if can_use_exec_cube(geo_filters):
        where, params = build_exec_cube_where(geo_filters)
        result = await session.execute(text(f"""
            SELECT
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                COUNT(DISTINCT customer_unique_id) AS total_customers,
                COALESCE(SUM(freight), 0) AS total_freight,
                COUNT(DISTINCT state_code) AS total_states
            FROM rpt_exec_orders{where}
        """), params)
        row = result.mappings().first()
        return dict(row) if row else {"total_revenue": 0, "total_orders": 0, "total_customers": 0, "total_freight": 0, "total_states": 0}

    query, params = build_dimensional_query(
        base_select="""
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            SUM(fs.freight_value) AS total_freight,
            COUNT(DISTINCT dg.state_code) AS total_states
        """,
        **geo_filters
    )
    result = await session.execute(text(query), params)
    row = result.mappings().first()
    return dict(row) if row else {"total_revenue": 0, "total_orders": 0, "total_customers": 0, "total_freight": 0, "total_states": 0}
