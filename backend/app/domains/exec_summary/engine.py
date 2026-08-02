"""
Analytica — Executive Summary Engine
Data-driven narrative generator.
Assembles a polished executive report from real analytics data,
with growth-aware sentiment, dynamic thresholds and actionable
recommendations that reference actual top performers.
"""

from app.domains.exec_summary.schemas import ReportSection, ExecutiveReport


def _pct(v: float | None) -> str:
    """Format a percentage change with explicit sign."""
    if v is None:
        return "n/a"
    return f"{v:+.1f}%"


def _sentiment_for_growth(growth: float | None) -> str:
    """Map a growth rate to a sentiment label."""
    if growth is None:
        return "neutral"
    if growth >= 5:
        return "positive"
    if growth <= -5:
        return "warning"
    return "neutral"


def _sentiment_for_share(share: float | None) -> str:
    """Concentration risk sentiment from a top-item revenue share."""
    if share is None:
        return "neutral"
    if share > 40:
        return "warning"
    if share < 20:
        return "positive"
    return "neutral"


def build_executive_report(
    exec_res,
    sales_res,
    cust_res,
    prod_res,
    geo_res,
    seg_res,
    fc_res,
    filters: dict | None = None,
) -> ExecutiveReport:
    """Assemble the full executive report from domain responses."""
    filters = filters or {}
    kpis = exec_res.kpis
    monthly_trend = exec_res.monthly_trend or []
    top_cats = exec_res.top_categories or []
    top_states = exec_res.top_states or []
    customer_snapshot = exec_res.customer_snapshot

    total_rev = kpis["total_revenue"].value
    total_orders = kpis["total_orders"].value
    total_cust = kpis["total_customers"].value
    aov = kpis["average_order_value"].value

    revenue_growth = kpis["total_revenue"].change_pct
    order_growth = kpis["total_orders"].change_pct

    # Real month count: when a specific month is selected the view is scoped to it;
    # otherwise count months that actually produced revenue in the trend.
    if filters.get("month"):
        num_months = 1
    else:
        num_months = max(sum(1 for m in monthly_trend if m.total_revenue > 0), 1)
    monthly_avg = total_rev / num_months

    best_month = None
    worst_month = None
    if monthly_trend:
        best_month = max(monthly_trend, key=lambda m: m.total_revenue)
        worst_month = min(monthly_trend, key=lambda m: m.total_revenue)

    seg_overview = seg_res.overview
    personas = seg_res.personas or []
    clusters = seg_res.clusters or []
    fc_meta = fc_res.metadata

    # --- Build sections ---
    sections: list[ReportSection] = []
    risks: list[str] = []
    opportunities: list[str] = []

    # 1. Revenue Performance
    rev_parts = [f"Total revenue reached R$ {total_rev:,.2f} across {int(total_orders):,} orders in {num_months} month(s) of activity (avg R$ {monthly_avg:,.2f}/month)."]
    if revenue_growth is not None:
        direction = "grew" if revenue_growth >= 0 else "declined"
        rev_parts.append(f"Month-over-month revenue {direction} by {abs(revenue_growth):.1f}%.")
    if order_growth is not None:
        rev_parts.append(f"Order volume {('rose' if order_growth >= 0 else 'fell')} {abs(order_growth):.1f}% over the same period.")
    if best_month and best_month.total_revenue > 0:
        rev_parts.append(f"Peak revenue month: {best_month.order_month} (R$ {best_month.total_revenue:,.2f}).")

    top_cat_name = top_cats[0].product_category if top_cats else None
    revenue_sentiment = _sentiment_for_growth(revenue_growth)
    sections.append(ReportSection(
        title="Revenue Performance",
        summary=" ".join(rev_parts),
        sentiment=revenue_sentiment,
        metrics=[
            f"R$ {total_rev:,.2f}",
            f"{int(total_orders):,} orders",
            f"R$ {aov:,.2f} AOV",
            f"{_pct(revenue_growth)} MoM",
        ],
        recommendation=(
            f"Double down on the {top_cat_name} category (largest driver) with targeted promotions and cross-selling bundles to lift AOV."
            if top_cat_name
            else "Focus on improving average order value through cross-selling and bundling strategies."
        ),
    ))

    # 2. Customer Health
    repeat_pct = getattr(customer_snapshot, "repeat_pct", 0.0)
    repeat_count = getattr(customer_snapshot, "repeat_customers", 0)
    at_risk = sum(c.customer_count for c in clusters if "Churned" in c.persona or "Dormant" in c.persona or "At-Risk" in c.persona or "Inactive" in c.persona)
    vip = sum(c.customer_count for c in clusters if "VIP" in c.persona)
    high_value = sum(c.customer_count for c in clusters if "High-Value Spenders" in c.persona)
    cluster_total = sum(c.customer_count for c in clusters) or 1

    # Persona / cluster counts come from a platform-wide ML model (not filter-scoped),
    # so their share is always computed against the full cluster population.
    at_risk_ratio = at_risk / cluster_total
    filtered_view = bool(filters)

    cust_parts = [f"{int(total_cust):,} active customers in this view, of which {int(repeat_count):,} ({repeat_pct:.1f}%) are repeat buyers."]
    if high_value or vip or at_risk:
        seg_bits = []
        if high_value:
            seg_bits.append(f"{int(high_value):,} High-Value")
        if vip:
            seg_bits.append(f"{int(vip):,} VIP")
        if at_risk:
            seg_bits.append(f"{int(at_risk):,} At-Risk")
        if seg_bits:
            scope = "Platform-wide ML personas: " if filtered_view else "ML personas: "
            cust_parts.append(scope + ", ".join(seg_bits) + ".")

    cust_sentiment = "warning" if at_risk_ratio > 0.4 or repeat_pct < 5 else ("positive" if repeat_pct > 20 else "neutral")

    if at_risk_ratio > 0.4:
        risks.append(f"{int(at_risk):,} customers ({at_risk_ratio*100:.1f}%) are Churned / Dormant platform-wide — win-back and re-engagement campaigns needed.")
    if repeat_pct < 10 and total_cust > 0:
        risks.append(f"Repeat purchase rate is only {repeat_pct:.1f}% in this view — retention is a key growth lever.")

    if high_value:
        opportunities.append(f"Nurture {int(high_value):,} High-Value customers toward VIP tier (avg AOV R$ {aov:,.2f}) via exclusive offers.")

    sections.append(ReportSection(
        title="Customer Health",
        summary=" ".join(cust_parts),
        sentiment=cust_sentiment,
        metrics=[
            f"{int(total_cust):,} total",
            f"{repeat_pct:.1f}% repeat",
            f"{int(vip):,} VIP",
            f"{at_risk_ratio*100:.1f}% at-risk",
        ],
        recommendation=(
            "Launch win-back campaigns for the Churned / Dormant segments and a loyalty program to convert one-time buyers into repeat customers."
            if at_risk_ratio > 0.4 or repeat_pct < 10
            else "Protect repeat buyers with a VIP loyalty program and referral incentives."
        ),
    ))

    # 3. Product Performance
    if top_cats:
        top_cat = top_cats[0]
        prod_parts = [f"Top category: {top_cat.product_category} (R$ {top_cat.total_revenue:,.2f}, {top_cat.revenue_share_pct:.1f}% of revenue)."]
        if len(top_cats) > 1:
            prod_parts.append(f"Top 3: {', '.join(c.product_category for c in top_cats[:3])}.")
        if top_cat.revenue_share_pct > 40:
            risks.append(f"Revenue concentration risk — {top_cat.product_category} alone drives {top_cat.revenue_share_pct:.1f}% of revenue.")

        sections.append(ReportSection(
            title="Product Performance",
            summary=" ".join(prod_parts),
            sentiment=_sentiment_for_share(top_cat.revenue_share_pct),
            metrics=[
                f"{top_cat.product_category} leads",
                f"{top_cat.revenue_share_pct:.1f}% share",
                f"{int(top_cat.total_orders):,} orders",
            ],
            recommendation=(
                f"Diversify the portfolio by promoting underperforming categories alongside the strong {top_cat.product_category} line to reduce concentration risk."
                if top_cat.revenue_share_pct > 40
                else f"Expand the top-performing {top_cat.product_category} category with targeted promotions and inventory optimization."
            ),
        ))
    else:
        sections.append(ReportSection(
            title="Product Performance",
            summary="No category data available for the current filters.",
            sentiment="neutral",
            metrics=[],
            recommendation="Expand catalog coverage or adjust filters to view category performance.",
        ))

    # 4. Geographic Distribution
    if top_states:
        top_state = top_states[0]
        total_state_rev = sum(s.total_revenue for s in top_states)
        top_share = (top_state.total_revenue / total_rev * 100) if total_rev > 0 else 0.0
        geo_parts = [f"Top state: {top_state.state_code} (R$ {top_state.total_revenue:,.2f}, {top_share:.1f}% of revenue)."]
        if len(top_states) > 1:
            geo_parts.append(f"Top 3: {', '.join(s.state_code for s in top_states[:3])}.")
        if top_share > 40:
            risks.append(f"Geographic concentration — {top_state.state_code} accounts for {top_share:.1f}% of revenue.")

        sections.append(ReportSection(
            title="Geographic Distribution",
            summary=" ".join(geo_parts),
            sentiment=_sentiment_for_share(top_share),
            metrics=[
                f"{top_state.state_code} leads",
                f"{top_share:.1f}% share",
                f"R$ {top_state.total_revenue:,.2f}",
            ],
            recommendation=(
                f"Reduce regional concentration by launching localized campaigns in states outside {top_state.state_code}."
                if top_share > 40
                else "Expand into underperforming states with localized campaigns and regional logistics optimization."
            ),
        ))
    else:
        sections.append(ReportSection(
            title="Geographic Distribution",
            summary="No regional data available for the current filters.",
            sentiment="neutral",
            metrics=[],
            recommendation="Expand regional coverage or adjust filters to view state-level performance.",
        ))

    # 5. Customer Segmentation (ML)
    silhouette = getattr(seg_overview, "silhouette_score", 0.0)
    persona_count = getattr(seg_overview, "persona_count", 0)
    cluster_count = getattr(seg_overview, "cluster_count", 0)
    if silhouette >= 0.5:
        seg_quality = "strong"
        seg_sentiment = "positive"
    elif silhouette >= 0.25:
        seg_quality = "moderate"
        seg_sentiment = "neutral"
    else:
        seg_quality = "weak"
        seg_sentiment = "warning"

    seg_parts = [f"ML segmentation identified {persona_count} persona(s) across {cluster_count} cluster(s)."]
    seg_parts.append(f"Silhouette score {silhouette:.3f} indicates {seg_quality} behavioral separation.")

    best_persona = None
    if personas:
        best_persona = max(personas, key=lambda p: p.total_revenue)
        seg_parts.append(f"Highest-revenue persona: {best_persona.persona} (R$ {best_persona.total_revenue:,.2f}).")

    if personas:
        opportunities.append(f"Leverage persona-based targeting across: {', '.join(p.persona for p in personas)}.")

    sections.append(ReportSection(
        title="Customer Segmentation (ML)",
        summary=" ".join(seg_parts),
        sentiment=seg_sentiment,
        metrics=[
            f"{persona_count} personas",
            f"{cluster_count} clusters",
            f"Silhouette {silhouette:.3f}",
        ],
        recommendation=(
            f"Apply persona-specific campaigns, prioritizing the {best_persona.persona} segment for immediate revenue impact."
            if best_persona
            else "Re-run the segmentation model on refreshed data to improve segment quality."
        ),
    ))

    # 6. Revenue Forecast
    fc_metrics = fc_meta.metrics
    monthly_fc = fc_res.monthly or []
    future_months = [m for m in monthly_fc if m.forecast_revenue is not None and m.forecast_revenue > 0]
    total_fc = sum(m.forecast_revenue for m in future_months)
    avg_fc = total_fc / len(future_months) if future_months else 0.0

    if fc_metrics.test_r2 >= 0.8:
        fc_quality = "high"
        fc_sentiment = "positive"
    elif fc_metrics.test_r2 >= 0.5:
        fc_quality = "moderate"
        fc_sentiment = "neutral"
    else:
        fc_quality = "low"
        fc_sentiment = "warning"

    _version = getattr(fc_meta, "model_version", None)
    if _version:
        if not str(_version).startswith("v"):
            _version = f"v{_version}"
        model_label = f"{fc_meta.algorithm} ({_version})"
    else:
        model_label = fc_meta.algorithm
    fc_parts = [
        f"{model_label} (R² = {fc_metrics.test_r2:.3f}, MAE = R$ {fc_metrics.test_mae:,.2f}) trained on {fc_meta.features} feature(s) from {fc_meta.history_start} to {fc_meta.history_end} shows {fc_quality} predictive reliability."
    ]
    if future_months:
        fc_parts.append(
            f"Forecast for the next {len(future_months)} month(s): R$ {total_fc:,.2f} total (avg R$ {avg_fc:,.2f}/month) through {fc_meta.forecast_end}."
        )
        opportunities.append(f"Use the {len(future_months)}-month forecast (avg R$ {avg_fc:,.2f}/mo) for inventory and budget planning.")

    sections.append(ReportSection(
        title="Revenue Forecast",
        summary=" ".join(fc_parts),
        sentiment=fc_sentiment,
        metrics=[
            f"R² = {fc_metrics.test_r2:.3f}",
            f"MAE = R$ {fc_metrics.test_mae:,.2f}",
            f"MAPE = {fc_metrics.test_mape:.1f}%",
        ],
        recommendation=(
            "Align procurement and marketing spend with forecasted revenue trends."
            if future_months
            else "Retrain the forecast model on additional historical data to improve reliability."
        ),
    ))

    # --- Executive narrative ---
    exec_parts = [
        f"This view generated R$ {total_rev:,.2f} in revenue from {int(total_orders):,} orders, with {int(total_cust):,} active customers and an average order value of R$ {aov:,.2f}."
    ]
    if revenue_growth is not None:
        exec_parts.append(
            f"Revenue {('expanded' if revenue_growth >= 0 else 'contracted')} {abs(revenue_growth):.1f}% month-over-month."
        )
    if top_cat_name:
        exec_parts.append(f"{top_cat_name} leads the portfolio and is the primary revenue driver.")
    if best_persona:
        exec_parts.append(f"The {best_persona.persona} persona is the highest-value customer segment.")
    if future_months:
        exec_parts.append(
            f"The forecasting model projects R$ {avg_fc:,.2f}/month over the next {len(future_months)} month(s), supporting continued growth planning."
        )

    growth_score = revenue_growth if revenue_growth is not None else 0
    overall = "positive" if growth_score >= 5 else ("warning" if growth_score <= -5 else "neutral")

    risk_items = risks or ["No significant risks detected in the current view."]
    opp_items = opportunities or ["Explore new market expansion strategies."]

    return ExecutiveReport(
        executive_summary=" ".join(exec_parts),
        sections=sections,
        key_risks=risk_items,
        opportunities=opp_items,
        overall_sentiment=overall,
    )
