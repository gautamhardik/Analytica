"""
Analytica — Insights Engine
Rule-based business intelligence generator.
Analyzes data and produces actionable insights with severity levels.
"""

from app.shared.schemas import Insight


def generate_executive_insights(
    total_revenue: float,
    total_orders: int,
    total_customers: int,
    revenue_growth: float | None,
    order_growth: float | None,
    top_category: str | None,
    top_state: str | None,
    top_state_revenue_share: float | None,
    repeat_customer_pct: float | None,
) -> list[Insight]:
    """Generate insights for the executive dashboard."""
    insights: list[Insight] = []

    # Revenue growth insight
    if revenue_growth is not None:
        if revenue_growth > 10:
            insights.append(Insight(
                type="growth",
                title=f"Revenue grew {revenue_growth:.1f}% month-over-month",
                detail=f"Strong upward momentum. Primary driver: {top_category or 'N/A'} category.",
                severity="positive",
            ))
        elif revenue_growth < -5:
            insights.append(Insight(
                type="growth",
                title=f"Revenue declined {abs(revenue_growth):.1f}% month-over-month",
                detail="Investigate potential causes: seasonal trends, category performance, or regional drops.",
                severity="critical",
            ))
        else:
            insights.append(Insight(
                type="growth",
                title=f"Revenue change: {revenue_growth:+.1f}% month-over-month",
                detail="Revenue is relatively stable compared to previous period.",
                severity="neutral",
            ))

    # Geographic concentration
    if top_state and top_state_revenue_share is not None:
        if top_state_revenue_share > 40:
            insights.append(Insight(
                type="warning",
                title=f"{top_state} accounts for {top_state_revenue_share:.1f}% of total revenue",
                detail="High geographic concentration risk. Consider expansion strategies in underperforming states.",
                severity="warning",
            ))
        else:
            insights.append(Insight(
                type="trend",
                title=f"Revenue is distributed across states (top state: {top_state} at {top_state_revenue_share:.1f}%)",
                detail="Healthy geographic diversification across the customer base.",
                severity="positive",
            ))

    # Repeat customers
    if repeat_customer_pct is not None:
        if repeat_customer_pct < 5:
            insights.append(Insight(
                type="segment",
                title=f"Only {repeat_customer_pct:.1f}% of customers are repeat buyers",
                detail="Consider loyalty programs, personalized recommendations, or re-engagement campaigns to improve retention.",
                severity="warning",
            ))
        elif repeat_customer_pct > 20:
            insights.append(Insight(
                type="segment",
                title=f"{repeat_customer_pct:.1f}% of customers are repeat buyers",
                detail="Strong customer loyalty. These repeat customers are a key revenue driver.",
                severity="positive",
            ))

    # Order volume
    if order_growth is not None and order_growth > 15:
        insights.append(Insight(
            type="growth",
            title=f"Order volume surged {order_growth:.1f}% month-over-month",
            detail="Ensure supply chain and fulfillment capacity can support increased demand.",
            severity="positive",
        ))

    return insights


def generate_sales_insights(
    categories: list[dict],
    monthly_trend: list[dict],
) -> list[Insight]:
    """Generate insights for the sales analytics domain."""
    insights: list[Insight] = []

    if categories:
        top = categories[0]
        bottom = categories[-1] if len(categories) > 1 else None
        insights.append(Insight(
            type="trend",
            title=f"Top performing category: {top.get('product_category', 'N/A')}",
            detail=f"Generated R$ {float(top.get('total_revenue', 0)):,.2f} in revenue with {int(top.get('total_orders', 0)):,} orders.",
            severity="positive",
        ))
        if bottom and float(bottom.get("total_revenue", 0)) > 0:
            insights.append(Insight(
                type="warning",
                title=f"Lowest performing category: {bottom.get('product_category', 'N/A')}",
                detail=f"Generated only R$ {float(bottom.get('total_revenue', 0)):,.2f}. Evaluate whether to optimize or phase out.",
                severity="warning",
            ))

    # Trend analysis
    if len(monthly_trend) >= 3:
        recent = monthly_trend[-1]
        prev = monthly_trend[-2]
        r_curr = float(recent.get("total_revenue", 0))
        r_prev = float(prev.get("total_revenue", 0))
        if r_prev > 0:
            change = ((r_curr - r_prev) / r_prev) * 100
            direction = "increased" if change > 0 else "decreased"
            insights.append(Insight(
                type="trend",
                title=f"Monthly revenue {direction} by {abs(change):.1f}%",
                detail=f"From R$ {r_prev:,.2f} to R$ {r_curr:,.2f} in the most recent period.",
                severity="positive" if change > 0 else "warning",
            ))

    return insights


def generate_customer_insights(
    total_customers: int,
    repeat_customers: int,
    one_time_customers: int,
    avg_spend: float,
) -> list[Insight]:
    """Generate insights for the customer analytics domain."""
    insights: list[Insight] = []

    repeat_pct = (repeat_customers / total_customers * 100) if total_customers > 0 else 0

    insights.append(Insight(
        type="segment",
        title=f"{repeat_pct:.1f}% repeat customer rate ({repeat_customers:,} of {total_customers:,})",
        detail="Repeat customers typically have higher lifetime value. Focus retention efforts on converting one-time buyers.",
        severity="positive" if repeat_pct > 10 else "warning",
    ))

    if avg_spend > 0:
        insights.append(Insight(
            type="trend",
            title=f"Average customer lifetime spend: R$ {avg_spend:,.2f}",
            detail="Consider upsell and cross-sell strategies for customers below average.",
            severity="neutral",
        ))

    return insights


def generate_geography_insights(
    states: list[dict],
    total_revenue: float,
) -> list[Insight]:
    """Generate insights for the geography analytics domain."""
    insights: list[Insight] = []

    if states and total_revenue > 0:
        top = states[0]
        top_rev = float(top.get("total_revenue", 0))
        top_share = (top_rev / total_revenue) * 100

        insights.append(Insight(
            type="trend",
            title=f"{top.get('state_code', 'N/A')} leads with R$ {top_rev:,.2f} ({top_share:.1f}% of total)",
            detail=f"Serving {int(top.get('total_customers', 0)):,} customers with {int(top.get('total_orders', 0)):,} orders.",
            severity="positive",
        ))

        # Bottom states
        if len(states) >= 5:
            bottom_5 = states[-5:]
            bottom_rev = sum(float(s.get("total_revenue", 0)) for s in bottom_5)
            bottom_share = (bottom_rev / total_revenue) * 100
            insights.append(Insight(
                type="warning",
                title=f"Bottom 5 states contribute only {bottom_share:.1f}% of revenue",
                detail="Significant untapped market potential in smaller states.",
                severity="warning",
            ))

    return insights
