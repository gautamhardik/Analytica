"""
Analytica — Customers Router
GET /api/v1/customers
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.customers.schemas import CustomersResponse, ReconciliationResponse
from app.domains.customers.service import get_customer_analytics, get_segment_reconciliation

router = APIRouter(prefix="/customers", tags=["Customer Analytics"])


@router.get("", response_model=CustomersResponse)
async def customer_analytics(
    month: str = Query(None, description="Month filter (e.g. 2018-05)"),
    state: str = Query(None, description="State code filter (e.g. SP)"),
    category: str = Query(None, description="Product category filter"),
    segment: str = Query(None, description="Customer segment filter"),
    seller: str = Query(None, description="Seller filter"),
    session: AsyncSession = Depends(get_session)
):
    """Customer Analytics — Segmentation, spending tiers, top customers, and insights."""
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v}
    return await get_customer_analytics(session, **filters)


@router.get("/segments-reconciliation", response_model=ReconciliationResponse)
async def segments_reconciliation(session: AsyncSession = Depends(get_session)):
    """Cross-Analytics mapping: rule-based segments vs ML personas."""
    return await get_segment_reconciliation(session)
