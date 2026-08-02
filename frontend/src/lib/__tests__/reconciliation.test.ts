import { describe, expect, it } from "vitest";
import { pivotReconciliation, ruleSegmentTotal, type ReconciliationCell } from "../reconciliation";

const matrix: ReconciliationCell[] = [
  { rule_segment: "new", persona: "Dormant / Inactive", customer_count: 41572, avg_confidence: 0.48, avg_lifetime_revenue: 120, avg_orders: 1, rule_share_within_persona: 98.2, persona_share_within_rule: 92.9 },
  { rule_segment: "new", persona: "High-Value Spenders", customer_count: 3183, avg_confidence: 0.4, avg_lifetime_revenue: 500, avg_orders: 1.5, rule_share_within_persona: 1.8, persona_share_within_rule: 7.1 },
  { rule_segment: "repeat", persona: "Dormant / Inactive", customer_count: 776, avg_confidence: 0.45, avg_lifetime_revenue: 800, avg_orders: 2.5, rule_share_within_persona: 1.8, persona_share_within_rule: 1.6 },
  { rule_segment: "repeat", persona: "High-Value Spenders", customer_count: 48750, avg_confidence: 0.5, avg_lifetime_revenue: 1200, avg_orders: 3, rule_share_within_persona: 98.2, persona_share_within_rule: 98.4 },
];

describe("pivotReconciliation", () => {
  it("groups rows by rule segment preserving the persona cell", () => {
    const rows = pivotReconciliation(matrix);
    expect(rows).toHaveLength(2);
    const newRow = rows.find((r) => r.rule === "new");
    expect(newRow).toBeDefined();
    expect(newRow!.cells["Dormant / Inactive"].customer_count).toBe(41572);
    expect(newRow!.cells["High-Value Spenders"].persona_share_within_rule).toBe(7.1);
  });

  it("handles null / undefined input", () => {
    expect(pivotReconciliation(null)).toEqual([]);
    expect(pivotReconciliation(undefined)).toEqual([]);
  });

  it("keeps rule order as first-seen in the flat list", () => {
    const rows = pivotReconciliation(matrix);
    expect(rows[0].rule).toBe("new");
    expect(rows[1].rule).toBe("repeat");
  });
});

describe("ruleSegmentTotal", () => {
  const composition = [
    { rule_segment: "new", customer_count: 44755 },
    { rule_segment: "repeat", customer_count: 49526 },
  ];

  it("returns the customer count for a rule segment", () => {
    expect(ruleSegmentTotal(composition, "new")).toBe(44755);
    expect(ruleSegmentTotal(composition, "repeat")).toBe(49526);
  });

  it("returns 0 for unknown segments or empty input", () => {
    expect(ruleSegmentTotal(composition, "vip")).toBe(0);
    expect(ruleSegmentTotal(null, "new")).toBe(0);
  });
});
