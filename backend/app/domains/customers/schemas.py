"""
Analytica — Customers Pydantic Schemas
"""

from pydantic import BaseModel
from app.shared.schemas import KPICard, Insight


class SpendingTier(BaseModel):
    tier: str
    customer_count: int
    tier_revenue: float
    avg_spend: float


class TopCustomer(BaseModel):
    customer_unique_id: str
    lifetime_revenue: float
    total_orders: int
    total_items_purchased: int
    average_order_value: float
    is_repeat_customer: bool


class CustomerSnapshot(BaseModel):
    total_customers: int
    repeat_customers: int
    one_time_customers: int
    repeat_pct: float


class CustomersResponse(BaseModel):
    """Aggregated customer analytics response."""
    kpis: dict[str, KPICard]
    snapshot: CustomerSnapshot
    spending_tiers: list[SpendingTier]
    top_customers: list[TopCustomer]
    insights: list[Insight]


class SegmentReconciliationRow(BaseModel):
    rule_segment: str
    persona: str
    customer_count: int
    avg_confidence: float
    avg_lifetime_revenue: float
    avg_orders: float
    rule_share_within_persona: float
    persona_share_within_rule: float


class PersonaCoherence(BaseModel):
    persona: str
    dominant_rule_segment: str
    dominant_share: float
    avg_confidence: float
    customer_count: int


class RuleSegmentComposition(BaseModel):
    rule_segment: str
    dominant_persona: str
    dominant_share: float
    avg_confidence: float
    customer_count: int


class ActionableCohort(BaseModel):
    id: str
    persona: str
    rule_segment: str
    customer_count: int
    avg_lifetime_revenue: float
    recommendation: str


class ReconciliationResponse(BaseModel):
    """Cross-tab of rule-based segments vs ML personas + coherence summary."""
    matrix: list[SegmentReconciliationRow]
    persona_coherence: list[PersonaCoherence]
    rule_segment_composition: list[RuleSegmentComposition]
    overall_agreement: float
    actionable_cohorts: list[ActionableCohort]
