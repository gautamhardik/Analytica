import asyncio
from app.core.database import async_session_factory
from app.domains.executive.service import get_executive_dashboard

async def check_segment():
    async with async_session_factory() as session:
        for seg in [None, "all", "new", "repeat", "vip"]:
            res = await get_executive_dashboard(session, segment=seg)
            rev = res.kpis["total_revenue"].formatted
            orders = res.kpis["total_orders"].formatted
            cust = res.kpis["total_customers"].formatted
            print(f"Segment '{seg}': Revenue={rev}, Orders={orders}, Customers={cust}")

if __name__ == "__main__":
    asyncio.run(check_segment())
