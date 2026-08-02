"""
Populate empty reporting tables from fact_sales_denormalized.
These tables are used by the unfiltered (no-filter) query paths.
"""
import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory


async def populate():
    async with async_session_factory() as s:
        async with s.begin():
            # 1. reporting_sales_summary (monthly aggregation)
            r = await s.execute(text("SELECT COUNT(*) FROM reporting_sales_summary"))
            count = r.scalar()
            if count == 0:
                print("Populating reporting_sales_summary...")
                await s.execute(text("""
                    INSERT INTO reporting_sales_summary
                        (year_number, month_number, order_month, total_revenue, total_orders, total_customers, average_order_value)
                    SELECT
                        year_number,
                        month_number,
                        month_year AS order_month,
                        SUM(total_sales_amount) AS total_revenue,
                        COUNT(DISTINCT order_id) AS total_orders,
                        COUNT(DISTINCT customer_unique_id) AS total_customers,
                        CASE WHEN COUNT(DISTINCT order_id) > 0
                             THEN SUM(total_sales_amount) / COUNT(DISTINCT order_id)
                             ELSE 0 END AS average_order_value
                    FROM fact_sales_denormalized
                    GROUP BY year_number, month_number, month_year
                    ORDER BY year_number, month_number
                """))
                r = await s.execute(text("SELECT COUNT(*) FROM reporting_sales_summary"))
                print(f"  reporting_sales_summary: {r.scalar()} rows")
            else:
                print(f"reporting_sales_summary already has {count} rows, skipping")

            # 2. reporting_category_summary
            r = await s.execute(text("SELECT COUNT(*) FROM reporting_category_summary"))
            count = r.scalar()
            if count == 0:
                print("Populating reporting_category_summary...")
                await s.execute(text("""
                    INSERT INTO reporting_category_summary
                        (product_category, total_revenue, total_orders, total_items_sold, average_item_price)
                    SELECT
                        product_category_name_english AS product_category,
                        SUM(total_sales_amount) AS total_revenue,
                        COUNT(DISTINCT order_id) AS total_orders,
                        SUM(quantity) AS total_items_sold,
                        CASE WHEN SUM(quantity) > 0
                             THEN SUM(total_sales_amount) / SUM(quantity)
                             ELSE 0 END AS average_item_price
                    FROM fact_sales_denormalized
                    WHERE product_category_name_english IS NOT NULL
                    GROUP BY product_category_name_english
                    ORDER BY total_revenue DESC
                """))
                r = await s.execute(text("SELECT COUNT(*) FROM reporting_category_summary"))
                print(f"  reporting_category_summary: {r.scalar()} rows")
            else:
                print(f"reporting_category_summary already has {count} rows, skipping")

            # 3. reporting_state_summary
            r = await s.execute(text("SELECT COUNT(*) FROM reporting_state_summary"))
            count = r.scalar()
            if count == 0:
                print("Populating reporting_state_summary...")
                await s.execute(text("""
                    INSERT INTO reporting_state_summary
                        (state_code, total_revenue, total_orders, total_customers, total_freight_cost)
                    SELECT
                        LEFT(state_code, 2) AS state_code,
                        SUM(total_sales_amount) AS total_revenue,
                        COUNT(DISTINCT order_id) AS total_orders,
                        COUNT(DISTINCT customer_unique_id) AS total_customers,
                        SUM(freight_value) AS total_freight_cost
                    FROM fact_sales_denormalized
                    WHERE state_code IS NOT NULL AND LENGTH(state_code) = 2
                    GROUP BY LEFT(state_code, 2)
                    ORDER BY total_revenue DESC
                """))
                r = await s.execute(text("SELECT COUNT(*) FROM reporting_state_summary"))
                print(f"  reporting_state_summary: {r.scalar()} rows")
            else:
                print(f"reporting_state_summary already has {count} rows, skipping")

            # Verify
            print("\nVerification:")
            for table in ["reporting_sales_summary", "reporting_category_summary", "reporting_state_summary"]:
                r = await s.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"  {table}: {r.scalar()} rows")

            # Sample data
            print("\nSample from reporting_sales_summary:")
            r = await s.execute(text("SELECT order_month, total_revenue, total_orders, total_customers FROM reporting_sales_summary LIMIT 5"))
            for row in r.mappings():
                print(f"  {row['order_month']}  rev={row['total_revenue']}  orders={row['total_orders']}  cust={row['total_customers']}")

            print("\nDone.")


if __name__ == "__main__":
    asyncio.run(populate())
