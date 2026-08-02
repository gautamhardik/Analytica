"""
Analytica — Schema Ensure Module
Creates the application tables/views required by the query layer and
populates empty reporting tables from the denormalized fact table.

Runs on startup for both MySQL and SQLite so a fresh deployment works
without manual migration steps.
"""

import logging
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger("analytica")

PREFERENCES_DDL = """
    CREATE TABLE IF NOT EXISTS preferences (
        `key` VARCHAR(128) PRIMARY KEY,
        `value` TEXT
    )
"""

DENORMALIZED_DDL = """
    CREATE TABLE IF NOT EXISTS fact_sales_denormalized AS
    SELECT
        fs.sales_key, fs.order_id, fs.order_item_id,
        fs.customer_key, fs.product_key, fs.seller_key,
        fs.purchase_date_key,
        fs.quantity, fs.price, fs.freight_value, fs.total_sales_amount,
        fs.etl_created_at, fs.etl_updated_at,
        COALESCE(dc.customer_unique_id, 'unknown') AS customer_unique_id,
        COALESCE(dcs.segment, 'unknown') AS segment,
        COALESCE(dg.state_code, 'unknown') AS state_code,
        COALESCE(dp.product_category_name_english, 'unknown') AS product_category_name_english,
        COALESCE(ds.seller_id, 'unknown') AS seller_id,
        COALESCE(dgs.city_name, 'unknown') AS seller_city,
        COALESCE(dgs.state_code, 'unknown') AS seller_state,
        dd.month_year, dd.year_number, dd.month_number
    FROM fact_sales fs
    LEFT JOIN dim_customer_segment dcs ON fs.customer_key = dcs.customer_key
    LEFT JOIN dim_customer dc ON fs.customer_key = dc.customer_key
    LEFT JOIN dim_geography dg ON dc.geography_key = dg.geography_key
    LEFT JOIN dim_product dp ON fs.product_key = dp.product_key
    LEFT JOIN dim_seller ds ON fs.seller_key = ds.seller_key
    LEFT JOIN dim_geography dgs ON ds.geography_key = dgs.geography_key
    LEFT JOIN dim_date dd ON fs.purchase_date_key = dd.date_key
"""

CUSTOMER_TABLE_DDL = [
    """CREATE TABLE IF NOT EXISTS reporting_filter_customer_orders (
        customer_unique_id VARCHAR(64),
        lifetime_revenue DECIMAL(32, 2),
        order_count BIGINT,
        total_items BIGINT,
        segment VARCHAR(50),
        state_code VARCHAR(16)
    )""",
]

POPULATE_CUSTOMER_ORDERS = """
    INSERT INTO reporting_filter_customer_orders
        (customer_unique_id, lifetime_revenue, order_count, total_items, segment, state_code)
    SELECT customer_unique_id,
           SUM(total_sales_amount),
           COUNT(DISTINCT order_id),
           SUM(quantity),
           MAX(segment),
           MAX(state_code)
    FROM fact_sales_denormalized
    GROUP BY customer_unique_id
"""

# ---------------------------------------------------------------------------
# Precomputed exec-summary cubes.
#
# Filtered dashboards repeatedly run COUNT(DISTINCT order_id) /
# COUNT(DISTINCT customer_unique_id) over large slices of
# fact_sales_denormalized, which is slow (disk-backed temp tables).  Instead
# we materialize:
#   * rpt_exec_orders      — one row per order (orders/revenue/freight roll up
#                            exactly because an order has a single
#                            segment/state/month; order count is COUNT(*)).
#   * rpt_cube_ssc         — segment x state x category (distinct order &
#                            customer counts are exact per cell; category
#                            rollups stay exact because an order/customer maps
#                            to one state).
#   * rpt_cube_seller      — segment x state x month x seller (per-seller
#                            orders/revenue, exact because each order occupies
#                            a single month and involves each seller once).
# ---------------------------------------------------------------------------
EXEC_CUBE_DDL = [
    """CREATE TABLE IF NOT EXISTS rpt_exec_orders (
        order_id VARCHAR(64) PRIMARY KEY,
        customer_unique_id VARCHAR(50),
        segment VARCHAR(50),
        state_code VARCHAR(16),
        month_year VARCHAR(10),
        revenue DECIMAL(32, 2),
        quantity BIGINT,
        freight DECIMAL(32, 2)
    )""",
    """CREATE TABLE IF NOT EXISTS rpt_cube_ssc (
        segment VARCHAR(50),
        state_code VARCHAR(16),
        category VARCHAR(64),
        revenue DECIMAL(32, 2),
        quantity BIGINT,
        orders BIGINT,
        customers BIGINT,
        PRIMARY KEY (segment, state_code, category)
    )""",
    """CREATE TABLE IF NOT EXISTS rpt_cube_seller (
        segment VARCHAR(50),
        state_code VARCHAR(16),
        month_year VARCHAR(10),
        seller_id VARCHAR(64),
        seller_city VARCHAR(64),
        seller_state VARCHAR(16),
        revenue DECIMAL(32, 2),
        quantity BIGINT,
        orders BIGINT,
        PRIMARY KEY (segment, state_code, month_year, seller_id)
    )""",
]

POPULATE_EXEC_CUBES = [
    """INSERT INTO rpt_exec_orders
        (order_id, customer_unique_id, segment, state_code, month_year, revenue, quantity, freight)
       SELECT order_id, MAX(customer_unique_id), MAX(segment), MAX(state_code), MAX(month_year),
              SUM(total_sales_amount), SUM(quantity), SUM(freight_value)
       FROM fact_sales_denormalized
       GROUP BY order_id""",
    """INSERT INTO rpt_cube_ssc
        (segment, state_code, category, revenue, quantity, orders, customers)
       SELECT segment, state_code, product_category_name_english,
              SUM(total_sales_amount), SUM(quantity), COUNT(DISTINCT order_id), COUNT(DISTINCT customer_unique_id)
       FROM fact_sales_denormalized
       WHERE product_category_name_english <> 'unknown'
       GROUP BY segment, state_code, product_category_name_english""",
    """INSERT INTO rpt_cube_seller
        (segment, state_code, month_year, seller_id, seller_city, seller_state, revenue, quantity, orders)
       SELECT segment, state_code, month_year, seller_id,
              MAX(seller_city), MAX(seller_state),
              SUM(total_sales_amount), SUM(quantity), COUNT(DISTINCT order_id)
       FROM fact_sales_denormalized
       WHERE seller_id <> 'unknown'
       GROUP BY segment, state_code, month_year, seller_id""",
]

EXEC_CUBE_INDEXES = [
    ("idx_ree_seg", "CREATE INDEX idx_ree_seg ON rpt_exec_orders (segment, state_code, month_year)"),
    ("idx_ree_month", "CREATE INDEX idx_ree_month ON rpt_exec_orders (month_year)"),
    ("idx_ree_cust", "CREATE INDEX idx_ree_cust ON rpt_exec_orders (customer_unique_id, revenue)"),
    ("idx_rsc_seg", "CREATE INDEX idx_rsc_seg ON rpt_cube_ssc (segment)"),
    ("idx_rsl_seg", "CREATE INDEX idx_rsl_seg ON rpt_cube_seller (segment, seller_id)"),
]


async def _create_index_if_missing(session, index_name: str, ddl: str) -> None:
    """Create an index only if it does not already exist (MySQL has no IF NOT EXISTS)."""
    if settings.db_type == "sqlite":
        ddl_sqlite = ddl.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1)
        await session.execute(text(ddl_sqlite))
        return
    result = await session.execute(
        text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND index_name = :i"
        ),
        {"i": index_name},
    )
    if result.scalar() is None:
        await session.execute(text(ddl))


async def _table_exists(session, table: str) -> bool:
    if settings.db_type == "sqlite":
        result = await session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = :t"),
            {"t": table},
        )
        return result.scalar() is not None
    result = await session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t"
        ),
        {"t": table},
    )
    return result.scalar() is not None


async def _count_rows(session, table: str) -> int:
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    return result.scalar() or 0


async def _widen_state_code(session) -> None:
    """Widen state_code on legacy deployments where it was VARCHAR(2).

    The 'unknown' fallback value (7 chars) does not fit in VARCHAR(2), so
    deployments that created reporting_filter_customer_orders before the fix
    need their column widened. Only MySQL needs this (SQLite ignores length).
    """
    if settings.db_type == "sqlite":
        return
    result = await session.execute(
        text(
            "SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'reporting_filter_customer_orders' "
            "AND column_name = 'state_code'"
        )
    )
    current = result.scalar()
    if current is not None and current < 16:
        await session.execute(
            text("ALTER TABLE reporting_filter_customer_orders MODIFY state_code VARCHAR(16)")
        )
        logger.info("Widened reporting_filter_customer_orders.state_code to VARCHAR(16)")


async def ensure_schema(session) -> None:
    """Create required tables and populate empty reporting tables."""
    # Preferences (portable DDL for MySQL + SQLite)
    await session.execute(text(PREFERENCES_DDL))

    # Denormalized fact table used by filtered query paths (fresh MySQL deploys)
    if not await _table_exists(session, "fact_sales_denormalized"):
        await session.execute(text(DENORMALIZED_DDL))
        logger.info("Built fact_sales_denormalized")

    # Create the customer-level reporting tables used by query paths
    for ddl in CUSTOMER_TABLE_DDL:
        await session.execute(text(ddl))
    await _widen_state_code(session)

    # reporting_filter_customer_orders feeds the segment/state filtered queries
    # and the rule-vs-ML reconciliation; rebuild when the fact table changes.
    if await _count_rows(session, "reporting_filter_customer_orders") == 0:
        await session.execute(text(POPULATE_CUSTOMER_ORDERS))
        logger.info("Populated reporting_filter_customer_orders")

    # Rebuild when the denormalized fact changes (e.g. after an ETL rerun), so
    # customer counts stay consistent with the deduped fact table.
    fact_customers = await session.scalar(
        text("SELECT COUNT(DISTINCT customer_unique_id) FROM fact_sales_denormalized")
    )
    if fact_customers is not None and await _count_rows(session, "reporting_filter_customer_orders") != fact_customers:
        await session.execute(text("DELETE FROM reporting_filter_customer_orders"))
        await session.execute(text(POPULATE_CUSTOMER_ORDERS))
        logger.info("Rebuilt reporting_filter_customer_orders from updated fact_sales_denormalized")

    # Main reporting tables (safe no-op when already populated by dump/migration)
    if await _count_rows(session, "reporting_sales_summary") == 0:
        await session.execute(text("""
            INSERT INTO reporting_sales_summary
                (year_number, month_number, order_month, total_revenue, total_orders, total_customers, average_order_value)
            SELECT year_number, month_number, month_year AS order_month,
                   SUM(total_sales_amount) AS total_revenue,
                   COUNT(DISTINCT order_id) AS total_orders,
                   COUNT(DISTINCT customer_unique_id) AS total_customers,
                   CASE WHEN COUNT(DISTINCT order_id) > 0
                        THEN SUM(total_sales_amount) / COUNT(DISTINCT order_id)
                        ELSE 0 END AS average_order_value
            FROM fact_sales_denormalized
            GROUP BY year_number, month_number, month_year
        """))

    if await _count_rows(session, "reporting_category_summary") == 0:
        await session.execute(text("""
            INSERT INTO reporting_category_summary
                (product_category, total_revenue, total_orders, total_items_sold, average_item_price)
            SELECT product_category_name_english AS product_category,
                   SUM(total_sales_amount) AS total_revenue,
                   COUNT(DISTINCT order_id) AS total_orders,
                   SUM(quantity) AS total_items_sold,
                   CASE WHEN SUM(quantity) > 0
                        THEN SUM(total_sales_amount) / SUM(quantity)
                        ELSE 0 END AS average_item_price
            FROM fact_sales_denormalized
            WHERE product_category_name_english IS NOT NULL
            GROUP BY product_category_name_english
        """))

    if await _count_rows(session, "reporting_state_summary") == 0:
        await session.execute(text("""
            INSERT INTO reporting_state_summary
                (state_code, total_revenue, total_orders, total_customers, total_freight_cost)
            SELECT LEFT(state_code, 2) AS state_code,
                   SUM(total_sales_amount) AS total_revenue,
                   COUNT(DISTINCT order_id) AS total_orders,
                   COUNT(DISTINCT customer_unique_id) AS total_customers,
                   SUM(freight_value) AS total_freight_cost
            FROM fact_sales_denormalized
            WHERE state_code IS NOT NULL AND LENGTH(state_code) = 2
            GROUP BY LEFT(state_code, 2)
        """))

    # Precomputed exec-summary cubes (created lazily, populated once)
    for ddl in EXEC_CUBE_DDL:
        await session.execute(text(ddl))
    fact_orders = await session.scalar(
        text("SELECT COUNT(DISTINCT order_id) FROM fact_sales_denormalized")
    )
    if fact_orders is not None and await _count_rows(session, "rpt_exec_orders") != fact_orders:
        await session.execute(text("DELETE FROM rpt_exec_orders"))
        await session.execute(text("DELETE FROM rpt_cube_ssc"))
        await session.execute(text("DELETE FROM rpt_cube_seller"))
    if await _count_rows(session, "rpt_exec_orders") == 0:
        await session.execute(text(POPULATE_EXEC_CUBES[0]))
        logger.info("Populated rpt_exec_orders")
    if await _count_rows(session, "rpt_cube_ssc") == 0:
        await session.execute(text(POPULATE_EXEC_CUBES[1]))
        logger.info("Populated rpt_cube_ssc")
    if await _count_rows(session, "rpt_cube_seller") == 0:
        await session.execute(text(POPULATE_EXEC_CUBES[2]))
        logger.info("Populated rpt_cube_seller")
    for index_name, index_ddl in EXEC_CUBE_INDEXES:
        await _create_index_if_missing(session, index_name, index_ddl)

    await session.commit()
