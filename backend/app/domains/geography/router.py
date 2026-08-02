"""
Analytica — Geography Router
GET /api/v1/geography
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.shared.schemas import APIResponse
from app.domains.geography.schemas import GeographyResponse
from app.domains.geography.service import get_geography_analytics

router = APIRouter(prefix="/geography", tags=["Geographic Analytics"])


@router.get("", response_model=APIResponse[GeographyResponse])
async def geography_analytics(
    session: AsyncSession = Depends(get_db),
    month: str = Query(None, description="Filter by month (YYYY-MM)"),
    state: str = Query(None, description="Filter by state code"),
    category: str = Query(None, description="Filter by product category"),
    segment: str = Query(None, description="Filter by customer segment"),
    seller: str = Query(None, description="Filter by seller ID"),
):
    """Geographic Analytics — State metrics, rankings, and insights."""
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v and v != "all"}
    data = await get_geography_analytics(session, **filters)
    return APIResponse(data=data)
