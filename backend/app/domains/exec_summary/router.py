import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.core.database import async_session_factory
from app.shared.schemas import APIResponse
from app.domains.executive.service import get_executive_dashboard
from app.domains.sales.service import get_sales_analytics
from app.domains.customers.service import get_customer_analytics
from app.domains.products.service import get_products_analytics
from app.domains.geography.service import get_geography_analytics
from app.domains.segmentation.service import get_segmentation_data as get_seg
from app.domains.forecasting.service import get_forecast
from app.domains.exec_summary.engine import build_executive_report
from app.domains.exec_summary.schemas import ExecutiveReport

router = APIRouter(tags=["executive-summary"])

from app.core.cache import get_cache, set_cache, make_cache_key


async def _run_with_session(service, **filters):
    async with async_session_factory() as session:
        return await service(session, **filters)


@router.get("/executive-summary", response_model=APIResponse)
async def ai_executive_summary(
    month: str = Query(None, description="Month filter (e.g. 2018-05)"),
    state: str = Query(None, description="State code filter (e.g. SP)"),
    category: str = Query(None, description="Product category filter"),
    segment: str = Query(None, description="Customer segment filter"),
    seller: str = Query(None, description="Seller filter"),
):
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v}
    cache_key = make_cache_key("ai_executive_summary", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    # The 7 domain services run independently, so fan them out across short-lived
    # sessions (a single AsyncSession is not safe for concurrent awaits).
    exec_res, sales_res, cust_res, prod_res, geo_res, seg_res, fc_res = await asyncio.gather(
        _run_with_session(get_executive_dashboard, **filters),
        _run_with_session(get_sales_analytics, **filters),
        _run_with_session(get_customer_analytics, **filters),
        _run_with_session(get_products_analytics, **filters),
        _run_with_session(get_geography_analytics, **filters),
        _run_with_session(get_seg),
        get_forecast(),
    )

    report = build_executive_report(
        exec_res=exec_res,
        sales_res=sales_res,
        cust_res=cust_res,
        prod_res=prod_res,
        geo_res=geo_res,
        seg_res=seg_res,
        fc_res=fc_res,
        filters=filters,
    ).model_copy(update={"generated_at": datetime.now(timezone.utc).isoformat()})

    response = APIResponse(data=report)
    set_cache(cache_key, response, ttl_seconds=300)
    return response
