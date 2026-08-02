from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.domains.forecasting.service import get_forecast
from app.domains.forecasting.schemas import ForecastResponse, DriftReport
from app.domains.forecasting.drift import compute_drift
from app.core.cache import get_cache, set_cache, make_cache_key

router = APIRouter(tags=["forecasting"])


@router.get("/forecasting/overview", response_model=ForecastResponse)
async def forecasting_overview(
    month: str = Query(None),
    state: str = Query(None),
    category: str = Query(None),
    segment: str = Query(None),
):
    return await get_forecast()


@router.get("/forecasting/drift", response_model=DriftReport)
async def forecasting_drift():
    """Feature-drift report comparing the recent data window to training stats."""
    cache_key = make_cache_key("forecasting_drift", {})
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    report = await run_in_threadpool(compute_drift)
    set_cache(cache_key, report, ttl_seconds=300)
    return report
