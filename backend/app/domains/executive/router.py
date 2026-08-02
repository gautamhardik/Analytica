"""
Analytica — Executive Router
GET /api/v1/executive — Returns the complete executive dashboard in one request.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.executive.schemas import ExecutiveResponse
from app.domains.executive.service import get_executive_dashboard

router = APIRouter(prefix="/executive", tags=["Executive"])


@router.get("", response_model=ExecutiveResponse)
async def executive_dashboard(
    month: str = Query(None, description="Month filter (e.g. 2018-05)"),
    state: str = Query(None, description="State code filter (e.g. SP)"),
    category: str = Query(None, description="Product category filter"),
    segment: str = Query(None, description="Customer segment filter"),
    seller: str = Query(None, description="Seller filter"),
    session: AsyncSession = Depends(get_session)
):
    """Get the comprehensive executive dashboard data."""
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v}
    return await get_executive_dashboard(session, **filters)
