import asyncio
from app.core.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT DISTINCT segment FROM fact_sales_denormalized"))
        segments = [r[0] for r in res.fetchall()]
        print("Distinct segments in DB:", segments)

        for s in ["new", "repeat", "vip"]:
            res2 = await session.execute(text("SELECT COUNT(*) FROM fact_sales_denormalized WHERE segment = :s"), {"s": s})
            print(f"Count for segment '{s}':", res2.scalar())

if __name__ == "__main__":
    asyncio.run(check())
