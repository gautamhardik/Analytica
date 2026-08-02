"""
Analytica — Products Router
GET /api/v1/products
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.shared.schemas import APIResponse
from app.domains.products.schemas import ProductsResponse
from app.domains.products.service import get_products_analytics

router = APIRouter(prefix="/products", tags=["Product & Seller Analytics"])


@router.get("", response_model=APIResponse[ProductsResponse])
async def products_analytics(
    session: AsyncSession = Depends(get_db),
    month: str = Query(None, description="Filter by month (YYYY-MM)"),
    state: str = Query(None, description="Filter by state code"),
    category: str = Query(None, description="Filter by product category"),
    segment: str = Query(None, description="Filter by customer segment"),
    seller: str = Query(None, description="Filter by seller ID"),
):
    """Product & Seller Analytics — Category performance, top sellers, and insights."""
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v and v != "all"}
    data = await get_products_analytics(session, **filters)
    return APIResponse(data=data)
