import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        r = await s.execute(text("SELECT DISTINCT segment FROM fact_sales_denormalized ORDER BY segment"))
        print("Distinct segments:", [row[0] for row in r.fetchall()])
        r2 = await s.execute(text("SELECT segment, COUNT(*) AS cnt FROM fact_sales_denormalized GROUP BY segment"))
        for row in r2.mappings():
            print(f"  {row['segment']}: {row['cnt']} rows")

        print("\n--- reporting_filter_customer_orders columns ---")
        r3 = await s.execute(text("SHOW COLUMNS FROM reporting_filter_customer_orders"))
        for row in r3:
            print(f"  {row[0]:30s} {row[1]}")

        print("\n--- reporting_sales_summary months ---")
        r4 = await s.execute(text("SELECT order_month, total_revenue, total_orders, total_customers FROM reporting_sales_summary ORDER BY order_month"))
        for row in r4.mappings():
            print(f"  {row['order_month']}  rev={row['total_revenue']}  orders={row['total_orders']}  cust={row['total_customers']}")

        print("\n--- reporting_filter_customer_orders state_code values ---")
        r5 = await s.execute(text("SELECT DISTINCT state_code FROM reporting_filter_customer_orders ORDER BY state_code"))
        print("States:", [row[0] for row in r5.fetchall()])

        print("\n--- reporting_filter_customer_orders segment values ---")
        r6 = await s.execute(text("SELECT DISTINCT segment FROM reporting_filter_customer_orders ORDER BY segment"))
        print("Segments:", [row[0] for row in r6.fetchall()])

        print("\n--- reporting_filter_customer_orders with state_code=SP ---")
        r7 = await s.execute(text("SELECT COUNT(*) FROM reporting_filter_customer_orders WHERE state_code = 'SP'"))
        print("SP customers:", r7.scalar())

        print("\n--- reporting_customer_overview ---")
        r8 = await s.execute(text("SELECT * FROM reporting_customer_overview"))
        for row in r8.mappings():
            print(f"  {dict(row)}")

asyncio.run(check())
