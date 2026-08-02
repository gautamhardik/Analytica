"use client";

import { useMemo, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Widget, WidgetHeader, WidgetBody, WidgetInsights, WidgetActions } from "@/components/ui/widget";
import { EmptyState } from "@/components/ui/empty-state";
import { InsightCard } from "@/components/ui/insight-card";
import { AreaChartWrapper } from "@/components/charts/area-chart-wrapper";
import { BarChartWrapper } from "@/components/charts/bar-chart-wrapper";
import { DollarSign, ShoppingCart, Users, CreditCard, ArrowRight, BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { formatCurrency, formatCurrencyCompact } from "@/lib/utils";
import Link from "next/link";
import { useAppStore } from "@/lib/store";
import { useToast } from "@/components/ui/toast";

export default function Dashboard() {
  const filters = useAppStore((state) => state.filters);
  const toast = useToast();

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v && v !== "all" && v !== "all_time") params.append(k, v);
    });
    return params;
  }, [filters]);

  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error, isFetching, refetch } = useQuery({
    queryKey: ["executive", queryString, filters],
    queryFn: () => fetcher<any>(`/executive${queryString}`),
  });

  // Notify on error
  useEffect(() => {
    if (error) {
      toast.push("Failed to load executive dashboard data.", "error");
    }
  }, [error, toast]);

  const monthlyTrendData = useMemo(() => data?.monthly_trend ?? [], [data?.monthly_trend]);
  const topCategoriesData = useMemo(() => (data?.top_categories ?? []).slice(0, 6), [data?.top_categories]);

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 pb-8">
        {/* Screen Reader ARIA Live Region for SC 4.1.3 Status Messages */}
        <div aria-live="polite" aria-atomic="true" className="sr-only">
          {isFetching ? "Updating dashboard metrics..." : "Dashboard metrics loaded successfully."}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-outfit font-extrabold tracking-tight text-gradient-gold">Executive Intelligence Dashboard</h1>
              {isFetching && !isLoading && <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse shadow-[0_0_10px_#f59e0b]" />}
            </div>
            <p className="text-muted-foreground text-sm mt-1">
              Enterprise performance analytics platform
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-32 rounded-xl bg-card/40 animate-pulse border border-border/50" />
              ))}
            </div>
            <div className="h-80 rounded-xl bg-card/40 animate-pulse border border-border/50" />
          </div>
        ) : error ? (
          <div className="p-6 bg-destructive/10 text-destructive rounded-xl border border-destructive/20">
            Failed to load executive data. Please check backend server.
          </div>
        ) : data ? (
          <>
            {/* KPI Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <KPICard
                title={filters.month || filters.state || filters.category || filters.segment ? "REVENUE (FILTERED)" : "TOTAL REVENUE"}
                value={data.kpis?.total_revenue?.formatted ?? "R$ 0.00"}
                change={filters.month ? data.kpis?.total_revenue?.change_pct : undefined}
                trend={filters.month ? (data.kpis?.total_revenue?.trend as any) : undefined}
                icon={<DollarSign className="w-5 h-5" />}
              />
              <KPICard
                title={filters.month || filters.state || filters.category || filters.segment ? "ORDERS (FILTERED)" : "TOTAL ORDERS"}
                value={data.kpis?.total_orders?.formatted ?? "0"}
                change={filters.month ? data.kpis?.total_orders?.change_pct : undefined}
                trend={filters.month ? (data.kpis?.total_orders?.trend as any) : undefined}
                icon={<ShoppingCart className="w-5 h-5" />}
              />
              <KPICard
                title={filters.month || filters.state || filters.category || filters.segment ? "CUSTOMERS (FILTERED)" : "TOTAL CUSTOMERS"}
                value={data.kpis?.total_customers?.formatted ?? "0"}
                icon={<Users className="w-5 h-5" />}
              />
              <KPICard
                title="AVERAGE ORDER VALUE"
                value={data.kpis?.average_order_value?.formatted ?? "R$ 0.00"}
                icon={<CreditCard className="w-5 h-5" />}
              />
            </div>

            {/* Visual Charts & Intelligence Split */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Revenue Trend Area Chart */}
              <Widget className="lg:col-span-2">
                <WidgetHeader 
                  title="Enterprise Revenue Trajectory" 
                  subtitle="Monthly aggregated sales volume across all product categories" 
                  onRefresh={refetch}
                />
                <WidgetBody className="h-[320px]">
                  {monthlyTrendData.length > 0 ? (
                    <AreaChartWrapper
                      data={monthlyTrendData}
                      xKey="order_month"
                      yKey="total_revenue"
                      yFormatter={(v) => formatCurrencyCompact(v)}
                      tooltipFormatter={(val: any) => [formatCurrency(val), "Gross Revenue"]}
                      gradientId="execColorRev"
                    />
                  ) : (
                    <EmptyState
                      title="No revenue data available"
                      description="Try adjusting the filters to see monthly revenue trends."
                      icon={<BarChart3 className="w-10 h-10" />}
                    />
                  )}
                </WidgetBody>
                <WidgetInsights>
                  {data.insights?.length > 0 ? (
                    <span className="text-sm">
                      <span className="font-semibold text-primary">Insight:</span> {data.insights[0].title}
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      No specific trends detected for current filters.
                    </span>
                  )}
                </WidgetInsights>
              </Widget>

              {/* Insights Summary Feed */}
              <Widget className="flex flex-col justify-between">
                <WidgetHeader 
                  title="Intelligence Feed" 
                  subtitle="Real-time automated findings"
                />
                <WidgetBody className="space-y-4 flex-1 overflow-y-auto pt-0">
                  {data.insights?.map((insight: any, i: number) => (
                    <InsightCard 
                      key={i}
                      observation={insight.title}
                      cause={insight.detail}
                      recommendation="Review strategy in affected segments."
                      trend={insight.severity === 'positive' ? 'up' : (insight.severity === 'critical' || insight.severity === 'warning') ? 'down' : 'neutral'}
                    />
                  ))}
                </WidgetBody>
                <WidgetActions className="border-t border-border/50 pt-4">
                  <Link href="/insights" className="text-xs text-primary font-medium flex items-center justify-between w-full hover:underline">
                    <span>View All Intelligence Rules</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </WidgetActions>
              </Widget>
            </div>

            {/* Bottom Row: Top Categories Breakdown */}
            <Widget>
              <WidgetHeader 
                title="Category Performance Leaderboard" 
                subtitle="Top revenue generating product categories"
              />
              <WidgetBody className="h-[320px] min-h-[320px] w-full pt-4 relative">
                {data.top_categories && data.top_categories.length > 0 ? (
                  <div className="w-full h-full min-h-[280px]">
                    <BarChartWrapper
                      data={topCategoriesData}
                      xKey="product_category"
                      yKey="total_revenue"
                      xFormatter={(val) => String(val).replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                      yFormatter={(v) => formatCurrencyCompact(v)}
                      tooltipFormatter={(val: any) => [formatCurrency(val), "Total Sales"]}
                      labelFormatter={(label) => String(label).replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                      gradientId="barColorCategory"
                      barSize={42}
                    />
                  </div>
                ) : (
                  <EmptyState
                    title="No category data available"
                    description="Try adjusting the filters to see category performance."
                    icon={<BarChart3 className="w-10 h-10" />}
                  />
                )}
              </WidgetBody>
              <WidgetActions className="border-t border-white/10 pt-4 justify-end">
                <Link href="/products" className="text-xs text-amber-400 font-semibold hover:underline flex items-center gap-1">
                  Explore Products <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </WidgetActions>
            </Widget>
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
