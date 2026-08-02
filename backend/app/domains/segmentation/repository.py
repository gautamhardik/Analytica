from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_segmentation_overview(session: AsyncSession) -> dict:
    result = await session.execute(text("""
        SELECT COUNT(*) AS total_customers,
               COUNT(DISTINCT cluster_id) AS cluster_count,
               COUNT(DISTINCT persona) AS persona_count
        FROM customer_segment_ml
    """))
    row = result.mappings().first()
    return dict(row) if row else {}



async def get_customer_segment(session: AsyncSession, customer_id: str) -> dict | None:
    result = await session.execute(
        text("""
            SELECT m.persona, m.cluster_id, m.confidence_score,
                   c.customer_unique_id,
                   COALESCE(SUM(f.total_sales_amount), 0) AS total_revenue,
                   COUNT(DISTINCT f.order_id) AS total_orders
            FROM dim_customer c
            LEFT JOIN customer_segment_ml m ON c.customer_unique_id = m.customer_unique_id
            LEFT JOIN fact_sales f ON c.customer_key = f.customer_key
            WHERE c.customer_unique_id = :cid
            GROUP BY m.persona, m.cluster_id, m.confidence_score, c.customer_unique_id
        """),
        {"cid": customer_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def get_customer_categories(session: AsyncSession, customer_id: str) -> list[str]:
    result = await session.execute(
        text("""
            SELECT DISTINCT p.product_category_name_english AS category
            FROM dim_customer c
            JOIN fact_sales f ON c.customer_key = f.customer_key
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE c.customer_unique_id = :cid
            ORDER BY category
        """),
        {"cid": customer_id},
    )
    return [row[0] for row in result.fetchall()]
