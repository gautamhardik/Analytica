export interface ReconciliationCell {
  rule_segment: string;
  persona: string;
  customer_count: number;
  avg_confidence: number;
  avg_lifetime_revenue: number;
  avg_orders: number;
  rule_share_within_persona: number;
  persona_share_within_rule: number;
}

export interface MatrixRow {
  rule: string;
  cells: Record<string, ReconciliationCell>;
}

/** Pivot the flat rule-segment x persona matrix into rows keyed by rule segment. */
export function pivotReconciliation(
  matrix: ReconciliationCell[] | null | undefined
): MatrixRow[] {
  const byRule: Record<string, Record<string, ReconciliationCell>> = {};
  (matrix ?? []).forEach((r) => {
    if (!byRule[r.rule_segment]) byRule[r.rule_segment] = {};
    byRule[r.rule_segment][r.persona] = r;
  });
  return Object.entries(byRule).map(([rule, cells]) => ({ rule, cells }));
}

/** Total customers for a rule segment from the composition summary. */
export function ruleSegmentTotal(
  composition: { rule_segment: string; customer_count: number }[] | null | undefined,
  rule: string
): number {
  return (composition ?? []).find((c) => c.rule_segment === rule)?.customer_count ?? 0;
}
