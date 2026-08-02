import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        r = await s.execute(text("SHOW COLUMNS FROM reporting_sales_summary"))
        for row in r:
            print(f"  {row[0]:40s} {row[1]:30s} {row[2] or ''}")

asyncio.run(check())
