export type MetricTrend = "up" | "down" | "neutral";
export type InsightSeverity = "positive" | "warning" | "critical" | "neutral";
export type UserRole = "executive" | "sales_manager" | "category_manager" | "regional_manager";

export interface KPICardData {
  label: string;
  value: number;
  formatted: string;
  change_pct?: number | null;
  trend: MetricTrend;
}

export interface ExecutiveDashboardData {
  kpis: {
    total_revenue: KPICardData;
    total_orders: KPICardData;
    total_customers: KPICardData;
    average_order_value: KPICardData;
  };
  monthly_trend: Array<{
    order_month: string;
    total_revenue: number;
    total_orders: number;
    total_customers: number;
    average_order_value: number;
  }>;
  top_categories: Array<{
    product_category: string;
    total_revenue: number;
    total_orders: number;
    total_items_sold: number;
    average_item_price: number;
    revenue_share_pct: number;
  }>;
  top_states: Array<{
    state_code: string;
    total_revenue: number;
    total_orders: number;
    total_customers: number;
    total_freight_cost: number;
  }>;
  insights: Array<{
    type: string;
    title: string;
    detail: string;
    severity: InsightSeverity;
  }>;
}
