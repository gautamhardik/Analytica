"""
Analytica — Customers Service
"""

import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.shared.schemas import KPICard
from app.shared.utils import format_currency, format_number, safe_float, safe_int
from app.domains.customers import repository
from app.domains.customers.schemas import (
    CustomersResponse, CustomerSnapshot, SpendingTier, TopCustomer,
    ReconciliationResponse, SegmentReconciliationRow, PersonaCoherence, RuleSegmentComposition, ActionableCohort,
)
from app.domains.insights.engine import generate_customer_insights


from app.core.cache import get_cache, set_cache, make_cache_key


@asynccontextmanager
async def _temp_session():
    async with async_session_factory() as s:
        yield s


async def get_customer_analytics(session: AsyncSession, **filters) -> CustomersResponse:
    """Assemble the complete customer analytics response."""
    cache_key = make_cache_key("customer_analytics", filters)
    cached_res = get_cache(cache_key)
    if cached_res:
        return cached_res

    async def _overview():
        async with _temp_session() as s:
            return await repository.get_customer_overview(s, **filters)

    async def _tiers():
        async with _temp_session() as s:
            return await repository.get_spending_tiers(s, **filters)

    async def _top():
        async with _temp_session() as s:
            return await repository.get_top_customers(s, limit=20, **filters)

    overview, tiers_data, top_data = await asyncio.gather(
        _overview(), _tiers(), _top(),
    )

    total = safe_int(overview.get("total_customers"))
    repeat = safe_int(overview.get("repeat_customers"))
    one_time = safe_int(overview.get("one_time_customers"))
    avg_spend = safe_float(overview.get("avg_lifetime_spend"))
    avg_orders = safe_float(overview.get("avg_orders_per_customer"))
    repeat_pct = (repeat / total * 100) if total > 0 else 0.0

    kpis = {
        "total_customers": KPICard(
            label="Total Customers", value=float(total), formatted=format_number(total),
        ),
        "repeat_customers": KPICard(
            label="Repeat Customers", value=float(repeat), formatted=format_number(repeat),
        ),
        "one_time_customers": KPICard(
            label="One-Time Customers", value=float(one_time), formatted=format_number(one_time),
        ),
        "avg_lifetime_spend": KPICard(
            label="Avg Lifetime Spend", value=avg_spend, formatted=format_currency(avg_spend),
        ),
        "avg_orders_per_customer": KPICard(
            label="Avg Orders/Customer", value=avg_orders, formatted=f"{avg_orders:.2f}",
        ),
    }

    snapshot = CustomerSnapshot(
        total_customers=total, repeat_customers=repeat,
        one_time_customers=one_time, repeat_pct=round(repeat_pct, 2),
    )

    tiers = [
        SpendingTier(
            tier=str(t.get("tier", "")),
            customer_count=safe_int(t.get("customer_count")),
            tier_revenue=safe_float(t.get("tier_revenue")),
            avg_spend=safe_float(t.get("avg_spend")),
        )
        for t in tiers_data
    ]

    top_customers = [
        TopCustomer(
            customer_unique_id=str(c.get("customer_unique_id", "")),
            lifetime_revenue=safe_float(c.get("lifetime_revenue")),
            total_orders=safe_int(c.get("total_orders")),
            total_items_purchased=safe_int(c.get("total_items_purchased")),
            average_order_value=safe_float(c.get("average_order_value")),
            is_repeat_customer=bool(c.get("is_repeat_customer")),
        )
        for c in top_data
    ]

    insights = generate_customer_insights(total, repeat, one_time, avg_spend)

    response = CustomersResponse(
        kpis=kpis, snapshot=snapshot, spending_tiers=tiers,
        top_customers=top_customers, insights=insights,
    )
    set_cache(cache_key, response, ttl_seconds=60)
    return response


async def get_segment_reconciliation(session: AsyncSession) -> ReconciliationResponse:
    """Reconcile rule-based segments (new/repeat/vip) with ML personas."""
    rows = await repository.get_segment_reconciliation(session)

    persona_totals: dict[str, int] = {}
    rule_totals: dict[str, int] = {}
    for r in rows:
        persona_totals[r["persona"]] = persona_totals.get(r["persona"], 0) + r["customer_count"]
        rule_totals[r["rule_segment"]] = rule_totals.get(r["rule_segment"], 0) + r["customer_count"]

    matrix = []
    for r in rows:
        persona_total = persona_totals.get(r["persona"], 0) or 1
        rule_total = rule_totals.get(r["rule_segment"], 0) or 1
        matrix.append(SegmentReconciliationRow(
            rule_segment=r["rule_segment"],
            persona=r["persona"],
            customer_count=r["customer_count"],
            avg_confidence=r["avg_confidence"],
            avg_lifetime_revenue=r["avg_lifetime_revenue"],
            avg_orders=r["avg_orders"],
            rule_share_within_persona=round(r["customer_count"] / persona_total * 100, 2),
            persona_share_within_rule=round(r["customer_count"] / rule_total * 100, 2),
        ))

    persona_coherence = []
    for persona, rows_p in _group_by(rows, "persona").items():
        rows_p_sorted = sorted(rows_p, key=lambda x: x["customer_count"], reverse=True)
        total = persona_totals.get(persona, 0) or 1
        conf = sum(r["customer_count"] * r["avg_confidence"] for r in rows_p_sorted) / total
        dominant = rows_p_sorted[0]
        persona_coherence.append(PersonaCoherence(
            persona=persona,
            dominant_rule_segment=dominant["rule_segment"],
            dominant_share=round(dominant["customer_count"] / total * 100, 2),
            avg_confidence=round(conf, 4),
            customer_count=total,
        ))
    persona_coherence.sort(key=lambda x: x.customer_count, reverse=True)

    rule_segment_composition = []
    for rule, rows_r in _group_by(rows, "rule_segment").items():
        rows_r_sorted = sorted(rows_r, key=lambda x: x["customer_count"], reverse=True)
        total = rule_totals.get(rule, 0) or 1
        conf = sum(r["customer_count"] * r["avg_confidence"] for r in rows_r_sorted) / total
        dominant = rows_r_sorted[0]
        rule_segment_composition.append(RuleSegmentComposition(
            rule_segment=rule,
            dominant_persona=dominant["persona"],
            dominant_share=round(dominant["customer_count"] / total * 100, 2),
            avg_confidence=round(conf, 4),
            customer_count=total,
        ))
    rule_segment_composition.sort(key=lambda x: x.customer_count, reverse=True)

    # Overall agreement = share of customers whose rule segment matches the
    # dominant rule segment of their assigned persona.
    persona_dominant: dict[str, str] = {p.persona: p.dominant_rule_segment for p in persona_coherence}
    agreed = sum(r["customer_count"] for r in rows if r["rule_segment"] == persona_dominant.get(r["persona"]))
    total_all = sum(rule_totals.values()) or 1

    # Actionable cohorts: gaps between the rule-based view and the ML personas
    # that map to concrete campaign follow-ups.
    def _cohort(cohort_id, persona_label, rule, recommendation, match):
        sel = [r for r in rows if match(r) and r["rule_segment"] == rule]
        n = sum(r["customer_count"] for r in sel)
        rev = sum(r["customer_count"] * r["avg_lifetime_revenue"] for r in sel)
        return ActionableCohort(
            id=cohort_id, persona=persona_label, rule_segment=rule, customer_count=n,
            avg_lifetime_revenue=round(rev / n, 2) if n else 0.0,
            recommendation=recommendation,
        )

    value_personas = ("VIP Loyalists", "High-Value Spenders")
    single_value = sum(r["customer_count"] for r in rows
                       if r["persona"] in value_personas and r["rule_segment"] == "new")
    dormant_vip = sum(r["customer_count"] for r in rows
                      if r["rule_segment"] == "vip" and ("Dormant" in r["persona"] or "Inactive" in r["persona"]))

    actionable_cohorts = [
        _cohort(
            "value_single_purchase",
            " / ".join(value_personas),
            "new",
            (f"{single_value:,} customers the ML model scores as high-value "
             "yet the rules flag as one-time 'new' buyers — prime candidates "
             "for a VIP onboarding / re-engagement flow."),
            lambda r: r["persona"] in value_personas,
        ),
        _cohort(
            "dormant_vip",
            "Dormant / Inactive",
            "vip",
            (f"{dormant_vip:,} rule-flagged VIP customers the ML model considers "
             "dormant — urgent win-back outreach recommended."),
            lambda r: "Dormant" in r["persona"] or "Inactive" in r["persona"],
        ),
    ]

    return ReconciliationResponse(
        matrix=matrix,
        persona_coherence=persona_coherence,
        rule_segment_composition=rule_segment_composition,
        overall_agreement=round(agreed / total_all * 100, 2),
        actionable_cohorts=[c for c in actionable_cohorts if c.customer_count > 0],
    )


def _group_by(rows: list[dict], key: str) -> dict:
    grouped: dict = {}
    for r in rows:
        grouped.setdefault(r[key], []).append(r)
    return grouped

