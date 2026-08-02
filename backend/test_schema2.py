import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        for table in ["reporting_category_summary", "reporting_state_summary", "reporting_customer_overview"]:
            print(f"\n--- {table} ---")
            r = await s.execute(text(f"SHOW COLUMNS FROM {table}"))
            for row in r:
                print(f"  {row[0]:40s} {row[1]:30s}")
            r2 = await s.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"  ROWS: {r2.scalar()}")

asyncio.run(check())
