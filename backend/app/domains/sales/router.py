"""
Analytica — Sales Router
GET /api/v1/sales — Revenue analytics and category performance.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.sales.schemas import SalesResponse
from app.domains.sales.service import get_sales_analytics

router = APIRouter(prefix="/sales", tags=["Sales Analytics"])

@router.get("", response_model=SalesResponse)
async def sales_analytics(
    month: str = Query(None, description="Month filter (e.g. 2018-05)"),
    state: str = Query(None, description="State code filter (e.g. SP)"),
    category: str = Query(None, description="Product category filter"),
    segment: str = Query(None, description="Customer segment filter"),
    seller: str = Query(None, description="Seller filter"),
    session: AsyncSession = Depends(get_session)
):
    """
    Sales Analytics — Revenue trends, category breakdown, and insights.
    """
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v}
    return await get_sales_analytics(session, **filters)
