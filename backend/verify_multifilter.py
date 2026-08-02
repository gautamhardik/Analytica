import asyncio
from app.core.database import async_session_factory
from app.domains.executive.repository import get_overall_kpis, get_monthly_trend

async def main():
    async with async_session_factory() as session:
        # Test single filters
        vip_kpis = await get_overall_kpis(session, segment='vip')
        print("VIP single filter KPIs:", vip_kpis)
        
        sp_kpis = await get_overall_kpis(session, state='SP')
        print("SP single filter KPIs:", sp_kpis)
        
        # Test combined multiple filters: segment='vip' AND state='SP' AND month='2018-05'
        multi_kpis = await get_overall_kpis(session, segment='vip', state='SP', month='2018-05')
        print("VIP + SP + 2018-05 Multi-Filter KPIs:", multi_kpis)

if __name__ == "__main__":
    asyncio.run(main())
