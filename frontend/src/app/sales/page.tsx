"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { InsightCard } from "@/components/ui/insight-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Widget, WidgetHeader, WidgetBody } from "@/components/ui/widget";
import { AreaChartWrapper } from "@/components/charts/area-chart-wrapper";
import { BarChartWrapper } from "@/components/charts/bar-chart-wrapper";
import { DollarSign, ShoppingCart, TrendingUp, Filter, BarChart3 } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { formatCurrency, formatCurrencyCompact } from "@/lib/utils";

export default function SalesPage() {
  const { setFilter, filters } = useAppStore();
  
  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sales", filters],
    queryFn: () => fetcher<any>(`/sales${queryString}`),

  });

  const handleCategoryClick = (data: any) => {
    if (data && data.activePayload && data.activePayload.length > 0) {
      setFilter("category", data.activePayload[0]?.payload?.product_category);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Sales Workspace</h1>
          <p className="text-muted-foreground">Revenue trends and category performance breakdown.</p>
        </div>

        {isLoading && !data ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : error ? (
          <div className="p-6 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            Failed to load sales data. Please check backend server.
          </div>
        ) : data ? (
          <>
            <div className="space-y-2">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 1. Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <KPICard
                title={data.kpis.total_revenue.label}
                value={data.kpis.total_revenue.formatted}
                change={data.kpis.total_revenue.change_pct}
                trend={data.kpis.total_revenue.trend}
                icon={<DollarSign className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.total_orders.label}
                value={data.kpis.total_orders.formatted}
                change={data.kpis.total_orders.change_pct}
                trend={data.kpis.total_orders.trend}
                icon={<ShoppingCart className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.average_order_value.label}
                value={data.kpis.average_order_value.formatted}
                change={data.kpis.average_order_value.change_pct}
                trend={data.kpis.average_order_value.trend}
                icon={<TrendingUp className="w-5 h-5" />}
              />
              </div>
            </div>

            <div className="space-y-2 pt-4">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 2. Analysis</h2>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Widget className="lg:col-span-2">
                  <WidgetHeader title="Revenue Trend" subtitle="Monthly sales performance" onRefresh={refetch} />
                  <WidgetBody className="h-[300px]">
                    {(data.monthly_trend ?? []).length > 0 ? (
                      <AreaChartWrapper
                        data={data.monthly_trend ?? []}
                        xKey="order_month"
                        yKey="total_revenue"
                        yFormatter={(v) => formatCurrencyCompact(v)}
                        tooltipFormatter={(val: any) => [formatCurrency(val), "Revenue"]}
                        gradientId="colorRevenue"
                        height={300}
                      />
                    ) : (
                      <EmptyState title="No sales trend data" icon={<BarChart3 className="w-10 h-10" />} />
                    )}
                  </WidgetBody>
                </Widget>

                <Widget>
                  <WidgetHeader title="Top Categories" subtitle="Click a bar to filter dashboard" />
                  <WidgetBody className="h-[300px]">
                    {(data.top_categories ?? []).length > 0 ? (
                      <BarChartWrapper
                        data={data.top_categories ?? []}
                        xKey="product_category"
                        yKey="total_revenue"
                        yFormatter={(v) => formatCurrencyCompact(v)}
                        tooltipFormatter={(val: any) => [formatCurrency(val), "Revenue"]}
                        height={300}
                        barSize={20}
                        onClick={handleCategoryClick}
                      />
                    ) : (
                      <EmptyState title="No category data" icon={<BarChart3 className="w-10 h-10" />} />
                    )}
                  </WidgetBody>
                </Widget>
              </div>
            </div>
            
            <div className="space-y-2 pt-4">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 3. Action</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {data.insights?.length > 0 ? data.insights.map((insight: any, i: number) => (
                  <InsightCard
                    key={i}
                    observation={insight.title}
                    cause={insight.detail}
                    recommendation="Review strategy based on trend analysis."
                    trend={insight.severity === 'positive' ? 'up' : insight.severity === 'critical' ? 'down' : 'neutral'}
                  />
                )) : (
                  <div className="col-span-2 p-6 text-center text-muted-foreground border border-dashed border-border/50 rounded-lg">
                    No specific insights generated for current filter selection.
                  </div>
                )}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
