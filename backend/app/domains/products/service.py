"""
Analytica — Products Service
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.schemas import KPICard, Insight
from app.shared.utils import format_currency, format_number, safe_float, safe_int
from app.domains.products import repository
from app.domains.products.schemas import ProductsResponse, CategoryDetail, SellerDetail


import asyncio
from app.core.cache import get_cache, set_cache, make_cache_key


async def get_products_analytics(session: AsyncSession, **filters) -> ProductsResponse:
    """Assemble the complete products/category analytics response."""
    cache_key = make_cache_key("products_analytics", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    categories_data = await repository.get_category_performance(session, **filters)
    sellers_data = await repository.get_seller_performance(session, limit=20, **filters)

    total_revenue = sum(safe_float(c.get("total_revenue")) for c in categories_data)
    total_categories = len(categories_data)
    total_items = sum(safe_int(c.get("total_items_sold")) for c in categories_data)

    kpis = {
        "total_categories": KPICard(
            label="Product Categories", value=float(total_categories),
            formatted=format_number(total_categories),
        ),
        "total_items_sold": KPICard(
            label="Total Items Sold", value=float(total_items),
            formatted=format_number(total_items),
        ),
        "total_revenue": KPICard(
            label="Total Revenue", value=total_revenue,
            formatted=format_currency(total_revenue),
        ),
    }

    categories = []
    for c in categories_data:
        rev = safe_float(c.get("total_revenue"))
        share = (rev / total_revenue * 100) if total_revenue > 0 else 0.0
        categories.append(CategoryDetail(
            product_category=str(c.get("product_category", "")),
            total_revenue=rev,
            total_orders=safe_int(c.get("total_orders")),
            total_items_sold=safe_int(c.get("total_items_sold")),
            average_item_price=safe_float(c.get("average_item_price")),
            revenue_share_pct=round(share, 2),
        ))

    top_sellers = [
        SellerDetail(
            seller_id=str(s.get("seller_id", "")),
            seller_state=s.get("seller_state"),
            seller_city=s.get("seller_city"),
            orders_fulfilled=safe_int(s.get("orders_fulfilled")),
            items_sold=safe_int(s.get("items_sold")),
            total_revenue_generated=safe_float(s.get("total_revenue_generated")),
        )
        for s in sellers_data
    ]

    # Insights
    insights: list[Insight] = []
    if categories:
        top = categories[0]
        insights.append(Insight(
            type="trend",
            title=f"Top category: {top.product_category}",
            detail=f"Generates {top.revenue_share_pct:.1f}% of total revenue with {top.total_orders:,} orders.",
            severity="positive",
        ))
    if len(categories) >= 2:
        bottom = categories[-1]
        insights.append(Insight(
            type="warning",
            title=f"Lowest category: {bottom.product_category}",
            detail=f"Only {bottom.revenue_share_pct:.1f}% revenue share. Evaluate product-market fit.",
            severity="warning",
        ))

    response = ProductsResponse(
        kpis=kpis, categories=categories,
        top_categories=categories[:5],
        bottom_categories=categories[-5:] if len(categories) > 10 else [],
        top_sellers=top_sellers, insights=insights,
    )
    set_cache(cache_key, response, ttl_seconds=60)
    return response

