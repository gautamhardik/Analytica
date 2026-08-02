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
def _can_use_cust_orders(filters: dict) -> bool:
    active = set(filters.keys())
    return active and active.issubset({"segment", "state"})

def _build_cust_where(filters: dict) -> tuple:
    clauses = []
    params = {}
    if "segment" in filters:
        clauses.append("segment = :segment")
        params["segment"] = filters["segment"]
    if "state" in filters:
        clauses.append("state_code = :state")
        params["state"] = filters["state"]
    return clauses, params


async def get_customer_overview(session: AsyncSession, **filters) -> dict:
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                COUNT(*) AS total_customers,
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COALESCE(AVG(lifetime_revenue), 0) AS avg_lifetime_spend,
                COALESCE(AVG(order_count), 0) AS avg_orders_per_customer
            FROM reporting_filter_customer_orders
        """))
        row = result.mappings().first()
        return dict(row) if row else {
            "total_customers": 0, "repeat_customers": 0, "one_time_customers": 0,
            "avg_lifetime_spend": 0, "avg_orders_per_customer": 0
        }

    if _can_use_cust_orders(filters):
        wc, p = _build_cust_where(filters)
        q = f"""
            SELECT
                COUNT(*) AS total_customers,
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COALESCE(AVG(lifetime_revenue), 0) AS avg_lifetime_spend,
                COALESCE(AVG(order_count), 0) AS avg_orders_per_customer
            FROM reporting_filter_customer_orders
            WHERE {" AND ".join(wc)}
        """
        result = await session.execute(text(q), p)
        row = result.mappings().first()
        return dict(row) if row else {
            "total_customers": 0, "repeat_customers": 0, "one_time_customers": 0,
            "avg_lifetime_spend": 0, "avg_orders_per_customer": 0
        }

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                COUNT(*) AS total_customers,
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS repeat_customers,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS one_time_customers,
                COALESCE(AVG(lifetime_revenue), 0) AS avg_lifetime_spend,
                COALESCE(AVG(order_count), 0) AS avg_orders_per_customer
            FROM (
                SELECT customer_unique_id, COUNT(*) AS order_count, SUM(revenue) AS lifetime_revenue
                FROM rpt_exec_orders{where}
                GROUP BY customer_unique_id
            ) AS customer_orders
        """), params)
        row = result.mappings().first()
        return dict(row) if row else {
            "total_customers": 0, "repeat_customers": 0, "one_time_customers": 0,
            "avg_lifetime_spend": 0, "avg_orders_per_customer": 0
        }

    sub_query, params = build_dimensional_query(
        base_select="""
            fs.customer_key,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            SUM(fs.total_sales_amount) AS lifetime_revenue
        """,
        group_by="fs.customer_key",
        **filters
    )
    full_query = f"""
        SELECT
            COUNT(*) AS total_customers,
            SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
            SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS one_time_customers,
            AVG(lifetime_revenue) AS avg_lifetime_spend,
            AVG(total_orders) AS avg_orders_per_customer
        FROM ({sub_query}) AS customer_orders
    """
    result = await session.execute(text(full_query), params)
    row = result.mappings().first()
    return dict(row) if row else {
        "total_customers": 0, "repeat_customers": 0, "one_time_customers": 0,
        "avg_lifetime_spend": 0, "avg_orders_per_customer": 0
    }


async def get_spending_tiers(session: AsyncSession, **filters) -> list[dict]:
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                CASE
                    WHEN lifetime_revenue < 50 THEN 'Under R$50'
                    WHEN lifetime_revenue < 100 THEN 'R$50 - R$100'
                    WHEN lifetime_revenue < 200 THEN 'R$100 - R$200'
                    WHEN lifetime_revenue < 500 THEN 'R$200 - R$500'
                    WHEN lifetime_revenue < 1000 THEN 'R$500 - R$1000'
                    ELSE 'R$1000+'
                END AS tier,
                COUNT(*) AS customer_count,
                SUM(lifetime_revenue) AS tier_revenue,
                AVG(lifetime_revenue) AS avg_spend
            FROM reporting_filter_customer_orders
            GROUP BY tier
            ORDER BY MIN(lifetime_revenue)
        """))
        return [dict(row) for row in result.mappings().all()]

    if _can_use_cust_orders(filters):
        wc, p = _build_cust_where(filters)
        q = f"""
            SELECT
                CASE
                    WHEN lifetime_revenue < 50 THEN 'Under R$50'
                    WHEN lifetime_revenue < 100 THEN 'R$50 - R$100'
                    WHEN lifetime_revenue < 200 THEN 'R$100 - R$200'
                    WHEN lifetime_revenue < 500 THEN 'R$200 - R$500'
                    WHEN lifetime_revenue < 1000 THEN 'R$500 - R$1000'
                    ELSE 'R$1000+'
                END AS tier,
                COUNT(*) AS customer_count,
                SUM(lifetime_revenue) AS tier_revenue,
                AVG(lifetime_revenue) AS avg_spend
            FROM reporting_filter_customer_orders
            WHERE {" AND ".join(wc)}
            GROUP BY tier
            ORDER BY MIN(lifetime_revenue)
        """
        result = await session.execute(text(q), p)
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        result = await session.execute(text(f"""
            SELECT
                CASE
                    WHEN lifetime_revenue < 50 THEN 'Under R$50'
                    WHEN lifetime_revenue < 100 THEN 'R$50 - R$100'
                    WHEN lifetime_revenue < 200 THEN 'R$100 - R$200'
                    WHEN lifetime_revenue < 500 THEN 'R$200 - R$500'
                    WHEN lifetime_revenue < 1000 THEN 'R$500 - R$1000'
                    ELSE 'R$1000+'
                END AS tier,
                COUNT(*) AS customer_count,
                SUM(lifetime_revenue) AS tier_revenue,
                AVG(lifetime_revenue) AS avg_spend
            FROM (
                SELECT customer_unique_id, SUM(revenue) AS lifetime_revenue
                FROM rpt_exec_orders{where}
                GROUP BY customer_unique_id
            ) AS customer_totals
            GROUP BY tier
            ORDER BY MIN(lifetime_revenue)
        """), params)
        return [dict(row) for row in result.mappings().all()]

    sub_query, params = build_dimensional_query(
        base_select="fs.customer_key, SUM(fs.total_sales_amount) as lifetime_revenue",
        group_by="fs.customer_key",
        **filters
    )
    full_query = f"""
        SELECT
            CASE
                WHEN lifetime_revenue < 50 THEN 'Under R$50'
                WHEN lifetime_revenue < 100 THEN 'R$50 - R$100'
                WHEN lifetime_revenue < 200 THEN 'R$100 - R$200'
                WHEN lifetime_revenue < 500 THEN 'R$200 - R$500'
                WHEN lifetime_revenue < 1000 THEN 'R$500 - R$1000'
                ELSE 'R$1000+'
            END AS tier,
            COUNT(*) AS customer_count,
            SUM(lifetime_revenue) AS tier_revenue,
            AVG(lifetime_revenue) AS avg_spend
        FROM ({sub_query}) AS customer_totals
        GROUP BY tier
        ORDER BY MIN(lifetime_revenue)
    """
    result = await session.execute(text(full_query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_top_customers(session: AsyncSession, limit: int = 20, **filters) -> list[dict]:
    if not _any_filter(filters):
        result = await session.execute(text("""
            SELECT
                customer_unique_id,
                lifetime_revenue,
                order_count AS total_orders,
                total_items AS total_items_purchased,
                CASE WHEN order_count > 0 THEN lifetime_revenue / order_count ELSE 0 END AS average_order_value,
                CASE WHEN order_count > 1 THEN 1 ELSE 0 END AS is_repeat_customer
            FROM reporting_filter_customer_orders
            ORDER BY lifetime_revenue DESC
            LIMIT :limit
        """), {"limit": limit})
        return [dict(row) for row in result.mappings().all()]

    if _can_use_cust_orders(filters):
        wc, p = _build_cust_where(filters)
        p["limit"] = limit
        q = f"""
            SELECT
                customer_unique_id,
                lifetime_revenue,
                order_count AS total_orders,
                total_items AS total_items_purchased,
                CASE WHEN order_count > 0 THEN lifetime_revenue / order_count ELSE 0 END AS average_order_value,
                CASE WHEN order_count > 1 THEN 1 ELSE 0 END AS is_repeat_customer
            FROM reporting_filter_customer_orders
            WHERE {" AND ".join(wc)}
            ORDER BY lifetime_revenue DESC
            LIMIT :limit
        """
        result = await session.execute(text(q), p)
        return [dict(row) for row in result.mappings().all()]

    if can_use_exec_cube(filters):
        where, params = build_exec_cube_where(filters)
        params["limit"] = limit
        result = await session.execute(text(f"""
            SELECT
                customer_unique_id,
                SUM(revenue) AS lifetime_revenue,
                COUNT(*) AS total_orders,
                SUM(quantity) AS total_items_purchased,
                CASE WHEN COUNT(*) > 0 THEN SUM(revenue) / COUNT(*) ELSE 0 END AS average_order_value,
                CASE WHEN COUNT(*) > 1 THEN 1 ELSE 0 END AS is_repeat_customer
            FROM rpt_exec_orders{where}
            GROUP BY customer_unique_id
            ORDER BY lifetime_revenue DESC
            LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]

    query, params = build_dimensional_query(
        base_select="""
            dc.customer_unique_id,
            SUM(fs.total_sales_amount) AS lifetime_revenue,
            COUNT(DISTINCT fs.order_id) AS total_orders,
            SUM(fs.quantity) AS total_items_purchased,
            SUM(fs.total_sales_amount) / COUNT(DISTINCT fs.order_id) AS average_order_value,
            CASE WHEN COUNT(DISTINCT fs.order_id) > 1 THEN 1 ELSE 0 END AS is_repeat_customer
        """,
        group_by="dc.customer_unique_id",
        order_by="lifetime_revenue DESC",
        limit=limit,
        **filters
    )
    result = await session.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


async def get_segment_reconciliation(session: AsyncSession) -> list[dict]:
    """Cross-tab of rule-based segments (reporting_filter_customer_orders)
    against ML personas (customer_segment_ml), keyed by customer_unique_id."""
    result = await session.execute(text("""
        SELECT
            COALESCE(r.segment, 'unassigned') AS rule_segment,
            COALESCE(s.persona, 'unassigned') AS persona,
            COUNT(*) AS customer_count,
            ROUND(AVG(s.confidence_score), 4) AS avg_confidence,
            ROUND(AVG(r.lifetime_revenue), 2) AS avg_lifetime_revenue,
            ROUND(AVG(r.order_count), 2) AS avg_orders
        FROM reporting_filter_customer_orders r
        LEFT JOIN customer_segment_ml s
            ON s.customer_unique_id = r.customer_unique_id
        GROUP BY r.segment, s.persona
        ORDER BY rule_segment, customer_count DESC
    """))
    return [dict(row) for row in result.mappings().all()]
