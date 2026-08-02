"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InsightCard } from "@/components/ui/insight-card";
import { Map, MapPin, Truck } from "lucide-react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from "recharts";

export default function GeographyPage() {
  const { filters } = useAppStore();

  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["geography", filters],
    queryFn: () => fetcher<any>(`/geography${queryString}`),
    placeholderData: keepPreviousData,
  });

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Geographic Analytics</h1>
          <p className="text-muted-foreground">State-level performance and freight distribution.</p>
        </div>

        {isLoading && !data ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : error ? (
          <div className="p-6 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            Failed to load geographic data. Please check backend server.
          </div>
        ) : data ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <KPICard
                title={data.kpis.total_states.label}
                value={data.kpis.total_states.formatted}
                icon={<Map className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.total_revenue.label}
                value={data.kpis.total_revenue.formatted}
                icon={<MapPin className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.total_freight.label}
                value={data.kpis.total_freight.formatted}
                icon={<Truck className="w-5 h-5" />}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Revenue by State (Top 10)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.top_states} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis dataKey="state_code" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `R$${Math.round((v ?? 0)/1000)}k`} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }}
                          cursor={{ fill: 'var(--muted)' }}
                          formatter={(value: any) => [`R$ ${(value ?? 0).toLocaleString()}`, 'Revenue']}
                        />
                        <Bar dataKey="total_revenue" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={36} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Freight Cost Distribution (Top 10 States)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.top_states ?? []} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis dataKey="state_code" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `R$${Math.round((v ?? 0)/1000)}k`} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }}
                          cursor={{ fill: 'var(--muted)' }}
                          formatter={(value: any) => [`R$ ${(value ?? 0).toLocaleString()}`, 'Freight Cost']}
                        />
                        <Bar dataKey="total_freight_cost" fill="#a78bfa" radius={[4, 4, 0, 0]} barSize={36} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {data.insights && data.insights.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {data.insights.map((insight: any, i: number) => (
                  <InsightCard
                    key={i}
                    observation={insight.title}
                    cause={insight.detail}
                    trend={insight.severity === 'positive' ? 'up' : (insight.severity === 'critical' || insight.severity === 'warning') ? 'down' : 'neutral'}
                  />
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
