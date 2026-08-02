"""
Analytica — Insights Router
GET /api/v1/insights — Consolidated business intelligence engine endpoint.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.shared.schemas import APIResponse
from app.domains.executive.service import get_executive_dashboard
from app.domains.sales.service import get_sales_analytics
from app.domains.customers.service import get_customer_analytics
from app.domains.products.service import get_products_analytics
from app.domains.geography.service import get_geography_analytics

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("")
async def get_all_insights(
    session: AsyncSession = Depends(get_db),
    month: str = Query(None, description="Month filter (e.g. 2018-05)"),
    state: str = Query(None, description="State code filter (e.g. SP)"),
    category: str = Query(None, description="Product category filter"),
    segment: str = Query(None, description="Customer segment filter"),
    seller: str = Query(None, description="Seller filter"),
):
    """Return consolidated business insights across all domains."""
    filters = {k: v for k, v in {"month": month, "state": state, "category": category, "segment": segment, "seller": seller}.items() if v}
    exec_res = await get_executive_dashboard(session, **filters)
    sales_res = await get_sales_analytics(session, **filters)
    cust_res = await get_customer_analytics(session, **filters)
    prod_res = await get_products_analytics(session, **filters)
    geo_res = await get_geography_analytics(session, **filters)

    all_insights = []
    
    for i in getattr(exec_res, "insights", []):
        all_insights.append({**i.model_dump(), "domain": "Executive"})
    for i in getattr(sales_res, "insights", []):
        all_insights.append({**i.model_dump(), "domain": "Sales"})
    for i in getattr(cust_res, "insights", []):
        all_insights.append({**i.model_dump(), "domain": "Customers"})
    for i in getattr(prod_res, "insights", []):
        all_insights.append({**i.model_dump(), "domain": "Products"})
    for i in getattr(geo_res, "insights", []):
        all_insights.append({**i.model_dump(), "domain": "Geography"})

    return APIResponse(data={"insights": all_insights, "total_insights": len(all_insights)})
