"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Widget, WidgetBody, WidgetHeader } from "@/components/ui/widget";
import { InsightCard } from "@/components/ui/insight-card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Users, UserPlus, UserCheck, Heart, Filter } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useMemo } from "react";
import { pivotReconciliation, ruleSegmentTotal } from "@/lib/reconciliation";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from "recharts";

export default function CustomersPage() {
  const { setFilter, filters } = useAppStore();
  
  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["customers", filters],
    queryFn: () => fetcher<any>(`/customers${queryString}`),
    placeholderData: keepPreviousData,
  });

  const { data: reconciliation } = useQuery({
    queryKey: ["customers-segments-reconciliation"],
    queryFn: () => fetcher<any>("/customers/segments-reconciliation"),
  });

  const personaOrder = useMemo(() => {
    const order: string[] = [];
    (reconciliation?.persona_coherence ?? []).forEach((p: any) => order.push(p.persona));
    return order;
  }, [reconciliation]);

  const matrixRows = useMemo(
    () => pivotReconciliation(reconciliation?.matrix),
    [reconciliation]
  );

  const handleTierClick = (data: any) => {
    if (data && data.activePayload && data.activePayload.length > 0) {
      const tier = data.activePayload[0]?.payload?.tier;
      const avgSpend = data.activePayload[0]?.payload?.avg_spend ?? 0;
      const segment = avgSpend < 100 ? 'new' : avgSpend < 500 ? 'repeat' : 'vip';
      setFilter("segment", segment);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Customer Workspace</h1>
          <p className="text-muted-foreground">Audience segmentation and lifetime value analysis.</p>
        </div>

        {isLoading && !data ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : error ? (
          <div className="p-6 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            Failed to load customer data. Please check backend server.
          </div>
        ) : data ? (
          <>
            <div className="space-y-2">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 1. Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <KPICard
                title={data.kpis.total_customers.label}
                value={data.kpis.total_customers.formatted}
                icon={<Users className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.repeat_customers.label}
                value={data.kpis.repeat_customers.formatted}
                icon={<UserCheck className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.avg_lifetime_spend.label}
                value={data.kpis.avg_lifetime_spend.formatted}
                icon={<Heart className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.avg_orders_per_customer.label}
                value={data.kpis.avg_orders_per_customer.formatted}
                icon={<UserPlus className="w-5 h-5" />}
              />
              </div>
            </div>

            <div className="space-y-2 pt-4">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 2. Analysis</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Widget>
                  <WidgetHeader title="Spending Tiers (LTV)" subtitle="Click a bar to filter by segment" onRefresh={refetch} />
                  <WidgetBody className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.spending_tiers} margin={{ top: 20, right: 30, left: 20, bottom: 5 }} onClick={handleTierClick} className="cursor-pointer">
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis dataKey="tier" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }}
                          cursor={{ fill: 'var(--muted)' }}
                          formatter={(value: any) => [(value ?? 0).toLocaleString(), 'Customers']}
                        />
                        <Bar dataKey="customer_count" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={40} />
                      </BarChart>
                    </ResponsiveContainer>
                  </WidgetBody>
                </Widget>

                <Widget className="flex flex-col justify-center p-8 bg-gradient-to-br from-card/50 to-primary/10">
                <div className="space-y-6">
                  <h3 className="text-xl font-outfit font-semibold">Customer Retention</h3>
                  <div className="flex items-end gap-4">
                    <span className="text-6xl font-bold tracking-tighter text-primary">
                      {data.snapshot?.repeat_pct ?? 0}%
                    </span>
                    <span className="text-muted-foreground pb-2">Repeat Rate</span>
                  </div>
                  
                  {/* Visual Progress Bar */}
                  <div className="w-full bg-black/10 rounded-full h-3 border border-border/50 overflow-hidden shadow-inner">
                    <div 
                      className="bg-primary h-full rounded-full transition-all duration-1000 ease-out" 
                      style={{ width: `${Math.max(data.snapshot?.repeat_pct ?? 0, 5)}%` }} 
                    />
                  </div>

                  <p className="text-muted-foreground leading-relaxed text-sm">
                    Out of                     <strong className="text-foreground">{(data.snapshot?.total_customers ?? 0).toLocaleString()}</strong> total customers, 
                    <strong className="text-foreground"> {(data.snapshot?.repeat_customers ?? 0).toLocaleString()}</strong> have purchased more than once.
                  </p>
                </div>
                </Widget>
              </div>
            </div>

            <div className="space-y-2 pt-4">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 3. Action</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(data.insights ?? []).length > 0 ? (
                  data.insights.map((insight: any, i: number) => (
                    <InsightCard
                      key={i}
                      observation={insight.title}
                      cause={insight.detail}
                      recommendation="Review strategy based on trend analysis."
                      trend={insight.severity === 'positive' ? 'up' : (insight.severity === 'critical' || insight.severity === 'warning') ? 'down' : 'neutral'}
                    />
                  ))
                ) : (
                  <>
                    <InsightCard
                      observation="Extremely low repeat purchase rate (~3%)."
                      cause="Lack of post-purchase engagement and loyalty incentives."
                      recommendation="Launch a targeted email campaign with a 10% discount for second purchases."
                      trend="down"
                      onActionClick={() => setFilter("segment", "new")}
                    />
                    <InsightCard
                      observation="VIP segment generates 40% of revenue."
                      cause="High-value customers are purchasing expensive electronics."
                      impact="Small drop in VIP retention will heavily impact revenue."
                      recommendation="Establish a dedicated account management flow for top 100 VIPs."
                      trend="up"
                      onActionClick={() => setFilter("segment", "vip")}
                    />
                  </>
                )}
              </div>
            </div>

            <div className="space-y-2 pt-4">
              <h2 className="text-sm font-semibold tracking-wider text-muted-foreground uppercase flex items-center gap-2"><Filter className="w-4 h-4"/> 4. Rule Segments vs ML Personas</h2>
              <div className="grid grid-cols-1 gap-6">
                <Widget>
                  <WidgetHeader
                    title="Segment Reconciliation"
                    subtitle={`Rule-based (new / repeat / vip) vs ML personas — ${reconciliation?.overall_agreement ?? "..."}% of customers fall in their persona's dominant rule segment`}
                  />
                  <WidgetBody>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Rule Segment</TableHead>
                          {personaOrder.map((p) => (
                            <TableHead key={p} className="text-right">{p}</TableHead>
                          ))}
                          <TableHead className="text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {matrixRows.map(({ rule, cells }) => (
                          <TableRow key={rule}>
                            <TableCell className="font-medium capitalize">{rule}</TableCell>
                            {personaOrder.map((p) => {
                              const cell = cells[p];
                              return (
                                <TableCell key={p} className="text-right">
                                  {cell ? (
                                    <span className="flex flex-col items-end">
                                      <span>{cell.customer_count.toLocaleString()}</span>
                                      <span className="text-xs text-muted-foreground">{cell.persona_share_within_rule.toFixed(1)}%</span>
                                    </span>
                                  ) : <span className="text-muted-foreground">—</span>}
                                </TableCell>
                              );
                            })}
                            <TableCell className="text-right font-medium">
                              {(() => { const t = ruleSegmentTotal(reconciliation?.rule_segment_composition, rule); return t ? t.toLocaleString() : "—"; })()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </WidgetBody>
                </Widget>
              </div>

              {(reconciliation?.actionable_cohorts?.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {reconciliation.actionable_cohorts.map((c: any) => (
                    <div key={c.id} className="rounded-xl bg-gradient-to-br from-amber-500/10 to-primary/5 border border-amber-500/25 p-5">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Actionable cohort</p>
                          <p className="text-2xl font-outfit font-bold">{c.customer_count.toLocaleString()} customers</p>
                        </div>
                        <div className="text-right text-sm text-muted-foreground">
                          <p className="capitalize font-medium text-foreground">{c.rule_segment}</p>
                          <p className="text-xs">{c.persona}</p>
                          <p className="text-xs">avg LTV R$ {c.avg_lifetime_revenue.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{c.recommendation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
