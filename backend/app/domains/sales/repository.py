"""
Analytica — Sales Repository
SQL queries for revenue analytics and category performance.
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
    return has_active_filters(filters, HAS_FILTERS)


async def get_sales_kpis(session: AsyncSession, **filters) -> dict:
    """Fetch overall revenue totals for KPI cards."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                COALESCE(SUM(total_revenue), 0) AS total_revenue,
                COALESCE(SUM(total_orders), 0) AS total_orders,
                CASE WHEN SUM(total_orders) > 0 THEN SUM(total_revenue) / SUM(total_orders) ELSE 0 END AS average_order_value
            FROM reporting_sales_summary
        """))
        row = result.mappings().first()
        return dict(row) if row else {"total_revenue": 0, "total_orders": 0, "average_order_value": 0}

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                CASE WHEN COUNT(*) > 0 THEN SUM(revenue) / COUNT(*) ELSE 0 END AS average_order_value
            FROM rpt_exec_orders{where}
        """), params)
        row = result.mappings().first()
        return dict(row) if row and row["total_revenue"] is not None else {
            "total_revenue": 0, "total_orders": 0, "average_order_value": 0
        }

    query, params = build_dimensional_query(
        base_select="""
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            CASE WHEN COUNT(DISTINCT fs.order_id) > 0 THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id) ELSE 0 END AS average_order_value
        """,
        **filters
    )
    result = await session.execute(text(query), params)
    row = result.mappings().first()
    return dict(row) if row and row["total_revenue"] is not None else {
        "total_revenue": 0, "total_orders": 0, "average_order_value": 0
    }

async def get_monthly_revenue_trend(session: AsyncSession, **filters) -> list[dict]:
    """Fetch monthly revenue trend with continuous date spine (no gaps)."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            WITH RECURSIVE date_spine AS (
                SELECT MIN(order_month) AS month_year FROM reporting_sales_summary
                UNION ALL
                SELECT DATE_FORMAT(
                    STR_TO_DATE(CONCAT(month_year, '-01'), '%Y-%m-%d') + INTERVAL 1 MONTH,
                    '%Y-%m'
                )
                FROM date_spine
                WHERE month_year < (SELECT MAX(order_month) FROM reporting_sales_summary)
            )
            SELECT
                d.month_year AS order_month,
                CAST(SUBSTRING(d.month_year, 1, 4) AS UNSIGNED) AS year_number,
                CAST(SUBSTRING(d.month_year, 6, 2) AS UNSIGNED) AS month_number,
                COALESCE(s.total_revenue, 0) AS total_revenue,
                COALESCE(s.total_orders, 0) AS total_orders,
                COALESCE(s.average_order_value, 0) AS average_order_value
            FROM date_spine d
            LEFT JOIN reporting_sales_summary s ON d.month_year = s.order_month
            ORDER BY d.month_year
        """))
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                month_year AS order_month,
                CAST(SUBSTRING(month_year, 1, 4) AS UNSIGNED) AS year_number,
                CAST(SUBSTRING(month_year, 6, 2) AS UNSIGNED) AS month_number,
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                CASE WHEN COUNT(*) > 0 THEN SUM(revenue) / COUNT(*) ELSE 0 END AS average_order_value
            FROM rpt_exec_orders{where}
            GROUP BY month_year
            ORDER BY month_year
        """), params)
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            dd.month_year AS order_month,
            dd.year_number,
            dd.month_number,
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            CASE WHEN COUNT(DISTINCT fs.order_id) > 0 THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id) ELSE 0 END AS average_order_value
        """,
        group_by="dd.month_year, dd.year_number, dd.month_number",
        order_by="dd.year_number, dd.month_number",
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]

async def get_category_performance(session: AsyncSession, limit: int = 8, **filters) -> list[dict]:
    """Fetch all category performance data."""
    if not _any_filter(filters):
        query = text("""
            SELECT product_category, total_revenue, total_orders, total_items_sold, average_item_price
            FROM reporting_category_summary
            ORDER BY total_revenue DESC
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        return [dict(row) for row in result.mappings().all()]

    # rpt_cube_ssc has no month column, so month-filtered category queries fall back to dimensional.
    if can_use_exec_cube(filters) and not has_active_filters(filters, {"month"}):
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
            LIMIT :limit
        """), {"limit": limit, **params})
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
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]

async def get_sales_by_state(session: AsyncSession, limit: int = 6, **filters) -> list[dict]:
    if not _any_filter(filters):
        query = text("""
            SELECT state_code, total_revenue, total_orders
            FROM reporting_state_summary
            ORDER BY total_revenue DESC
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                state_code,
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders
            FROM rpt_exec_orders{where}
            GROUP BY state_code
            ORDER BY total_revenue DESC
            LIMIT :limit
        """), {"limit": limit, **params})
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            dg.state_code,
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders
        """,
        group_by="dg.state_code",
        order_by="total_revenue DESC",
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]
