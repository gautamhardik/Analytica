"""
Analytica — Executive Repository
Raw SQL queries against reporting tables for the executive overview.
Falls back to dimensional fact_sales queries when filters require it.
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


async def get_overall_kpis(session: AsyncSession, **filters) -> dict:
    """Fetch aggregated top-line KPIs. Uses reporting_sales_summary when unfiltered."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                COALESCE(SUM(total_revenue), 0) AS total_revenue,
                COALESCE(SUM(total_orders), 0) AS total_orders,
                COALESCE((SELECT COUNT(*) FROM reporting_filter_customer_orders), 0) AS total_customers,
                CASE WHEN SUM(total_orders) > 0
                     THEN SUM(total_revenue) / SUM(total_orders)
                     ELSE 0 END AS average_order_value
            FROM reporting_sales_summary
        """))
        row = result.mappings().first()
        return dict(row) if row else {"total_revenue": 0, "total_orders": 0, "total_customers": 0, "average_order_value": 0}

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                COUNT(DISTINCT customer_unique_id) AS total_customers,
                CASE WHEN COUNT(*) > 0 THEN SUM(revenue) / COUNT(*) ELSE 0 END AS average_order_value
            FROM rpt_exec_orders{where}
        """), params)
        row = result.mappings().first()
        return dict(row) if row and row["total_revenue"] is not None else {
            "total_revenue": 0, "total_orders": 0, "total_customers": 0, "average_order_value": 0
        }

    query, params = build_dimensional_query(
        base_select="""
            SUM(fs.total_sales_amount) AS total_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            CASE WHEN COUNT(DISTINCT fs.order_id) > 0 THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id) ELSE 0 END AS average_order_value
        """,
        **filters
    )
    result = await session.execute(text(query), params)
    row = result.mappings().first()
    return dict(row) if row and row["total_revenue"] is not None else {
        "total_revenue": 0, "total_orders": 0, "total_customers": 0, "average_order_value": 0
    }


async def get_monthly_trend(session: AsyncSession, **filters) -> list[dict]:
    """Fetch monthly sales trend with continuous date spine (no gaps).
    
    Month filter is intentionally ignored for the trend — it always shows all months
    so users can see the full trajectory with the selected month highlighted in context.
    Other filters (state, category, segment, seller) still apply.
    """
    trend_filters = {k: v for k, v in filters.items() if k != "month"}
    has_non_month_filters = has_active_filters(trend_filters, HAS_FILTERS - {"month"})

    if not has_non_month_filters:
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
                COALESCE(s.total_customers, 0) AS total_customers,
                COALESCE(s.average_order_value, 0) AS average_order_value
            FROM date_spine d
            LEFT JOIN reporting_sales_summary s ON d.month_year = s.order_month
            ORDER BY d.month_year
        """))
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(trend_filters):
        where, params = build_exec_cube_where(trend_filters)
        result = await session.execute(text(f"""
            SELECT
                month_year AS order_month,
                CAST(SUBSTRING(month_year, 1, 4) AS UNSIGNED) AS year_number,
                CAST(SUBSTRING(month_year, 6, 2) AS UNSIGNED) AS month_number,
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                COUNT(DISTINCT customer_unique_id) AS total_customers,
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
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            CASE WHEN COUNT(DISTINCT fs.order_id) > 0 THEN SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id) ELSE 0 END AS average_order_value
        """,
        group_by="dd.month_year, dd.year_number, dd.month_number",
        order_by="dd.year_number, dd.month_number",
        **trend_filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_top_categories(session: AsyncSession, limit: int = 5, **filters) -> list[dict]:
    """Fetch top N product categories by revenue. Uses reporting_category_summary when unfiltered."""
    if not _any_filter(filters):
        query = text("""
            SELECT
                product_category,
                total_revenue,
                total_orders,
                total_items_sold,
                average_item_price
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
                SUM(customers) AS total_customers,
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
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            CASE WHEN SUM(fs.quantity) > 0 THEN SUM(fs.total_sales_amount) / SUM(fs.quantity) ELSE 0 END AS average_item_price
        """,
        group_by="dp.product_category_name_english",
        order_by="total_revenue DESC",
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_top_states(session: AsyncSession, limit: int = 5, **filters) -> list[dict]:
    """Fetch top N states by revenue. Uses reporting_state_summary when unfiltered."""
    if not _any_filter(filters):
        query = text("""
            SELECT
                state_code,
                total_revenue,
                total_orders,
                total_customers,
                total_freight_cost
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
                COUNT(*) AS total_orders,
                COUNT(DISTINCT customer_unique_id) AS total_customers,
                COALESCE(SUM(freight), 0) AS total_freight_cost
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
            COUNT(DISTINCT fs.order_id) AS total_orders,
            COUNT(DISTINCT fs.customer_unique_id) AS total_customers,
            SUM(fs.freight_value) AS total_freight_cost
        """,
        group_by="dg.state_code",
        order_by="total_revenue DESC",
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_customer_snapshot(session: AsyncSession, **filters) -> dict:
    """Fetch repeat vs one-time customer breakdown."""
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COUNT(*) AS total_customers
            FROM reporting_filter_customer_orders
        """))
        row = result.mappings().first()
        return dict(row) if row else {"repeat_customers": 0, "one_time_customers": 0, "total_customers": 0}

    only_seg = set(filters) == {"segment"}
    only_state = set(filters) == {"state"}
    seg_state = set(filters) == {"segment", "state"}
    use_cust_orders = only_seg or only_state or seg_state
    if use_cust_orders:
        where_clauses = []
        params = {}
        if "segment" in filters:
            where_clauses.append("segment = :segment")
            params["segment"] = filters["segment"]
        if "state" in filters:
            where_clauses.append("state_code = :state")
            params["state"] = filters["state"]
        q = f"""
            SELECT
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COUNT(*) AS total_customers
            FROM reporting_filter_customer_orders
            WHERE {" AND ".join(where_clauses)}
        """
        result = await session.execute(text(q), params)
        row = result.mappings().first()
        return dict(row) if row else {"repeat_customers": 0, "one_time_customers": 0, "total_customers": 0}

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COUNT(*) AS total_customers
            FROM (
                SELECT customer_unique_id, COUNT(*) AS order_count
                FROM rpt_exec_orders{where}
                GROUP BY customer_unique_id
            ) AS customer_orders
        """), params)
        row = result.mappings().first()
        return dict(row) if row else {"repeat_customers": 0, "one_time_customers": 0, "total_customers": 0}

    sub_query, params = build_dimensional_query(
        base_select="fs.customer_unique_id, COUNT(DISTINCT fs.order_id) as order_count",
        group_by="fs.customer_unique_id",
        **filters
    )
    full_query = f"""
        SELECT 
            SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
            SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END) AS one_time_customers,
            COUNT(*) AS total_customers
        FROM ({sub_query}) AS customer_orders
    """
    result = await session.execute(text(full_query), params)
    row = result.mappings().first()
    return dict(row) if row else {"repeat_customers": 0, "one_time_customers": 0, "total_customers": 0}
