"""
Analytica — Products Repository
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


def _any_filter(filters: dict) -> bool:
    """Return True when at least one meaningful filter value is present.

    Treat values like 'all', 'all_time', 'none', 'null', or empty strings as no-filter.
    """
    if not filters:
        return False
    for k in HAS_FILTERS:
        if k in filters:
            v = filters.get(k)
            if v is None:
                continue
            sv = str(v).strip().lower()
            if sv in ("all", "all_time", "none", "null", ""):
                continue
            return True
    return False


async def get_category_performance(session: AsyncSession, **filters) -> list[dict]:
    """All categories ordered by revenue."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                product_category,
                total_revenue,
                total_orders,
                total_items_sold,
                average_item_price
            FROM reporting_category_summary
            ORDER BY total_revenue DESC
        """))
        return [dict(row) for row in result.mappings().all()]

    # rpt_cube_ssc has no month column, so month-filtered category queries fall back to dimensional.
    if can_use_exec_cube(filters) and not has_active_filters_month(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                category AS product_category,
                SUM(revenue) AS total_revenue,
                SUM(orders) AS total_orders,
                SUM(quantity) AS total_items_sold,
                CASE WHEN SUM(quantity) > 0 THEN SUM(revenue) / SUM(quantity) ELSE 0 END AS average_item_price
            FROM rpt_cube_ssc{where}
            GROUP BY category
            ORDER BY total_revenue DESC
        """), params)
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            dp.product_category_name_english AS product_category,
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            SUM(fs.quantity) AS total_items_sold,
            CASE WHEN SUM(fs.quantity) > 0 THEN SUM(fs.total_sales_amount) / SUM(fs.quantity) ELSE 0 END AS average_item_price
        """,
        group_by="dp.product_category_name_english",
        order_by="total_revenue DESC",
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


def has_active_filters_month(filters: dict) -> bool:
    """Return True when a meaningful month filter is present."""
    return has_active_filters(filters, {"month"})


async def get_seller_performance(session: AsyncSession, limit: int = 20, **filters) -> list[dict]:
    """Top sellers by revenue."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                seller_id,
                seller_state,
                seller_city,
                orders_fulfilled,
                items_sold,
                total_revenue_generated
            FROM reporting_seller_summary
            ORDER BY total_revenue_generated DESC
            LIMIT :limit
        """), {"limit": limit})
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                seller_id,
                MAX(seller_city) AS seller_city,
                MAX(seller_state) AS seller_state,
                SUM(orders) AS orders_fulfilled,
                SUM(quantity) AS items_sold,
                SUM(revenue) AS total_revenue_generated
            FROM rpt_cube_seller{where}
            GROUP BY seller_id
            ORDER BY total_revenue_generated DESC
            LIMIT :limit
        """), {"limit": limit, **params})
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            ds.seller_id,
            ds.seller_city,
            ds.seller_state,
            COUNT(DISTINCT fs.order_id) AS orders_fulfilled,
            SUM(fs.quantity) AS items_sold,
            SUM(fs.total_sales_amount) AS total_revenue_generated
        """,
        group_by="ds.seller_id, ds.seller_city, ds.seller_state",
        order_by="total_revenue_generated DESC",
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]
