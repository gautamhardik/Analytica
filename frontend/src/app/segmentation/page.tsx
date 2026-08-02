"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Widget, WidgetHeader, WidgetBody } from "@/components/ui/widget";
import { InsightCard } from "@/components/ui/insight-card";
import { Layers, Users, TrendingUp, Target, Search, User } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { useState } from "react";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, BarChart, Bar, PieChart, Pie, Legend,
} from "recharts";

import { PERSONA_COLORS } from "@/lib/constants";

export default function SegmentationPage() {
  const { filters } = useAppStore();
  const [searchId, setSearchId] = useState("");
  const [lookupId, setLookupId] = useState("");

  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading } = useQuery({
    queryKey: ["segmentation", filters],
    queryFn: () => fetcher<any>(`/segmentation/overview${queryString}`),
  });

  const { data: customerData, isLoading: customerLoading } = useQuery({
    queryKey: ["customer-segment", lookupId],
    queryFn: () => fetcher<any>(`/customers/${lookupId}/segment`),
    enabled: !!lookupId,
  });

  const overview = data?.overview;
  const clusters = data?.clusters ?? [];
  const personas = data?.personas ?? [];
  const pcaPoints = data?.pca_projection ?? [];

  const revenueByPersona = personas.map((p: any) => ({
    name: p.persona,
    value: Math.round(p.total_revenue),
    fill: PERSONA_COLORS[p.persona] ?? "#888",
  }));

  const customerByPersona = personas.map((p: any) => ({
    name: p.persona,
    count: p.customer_count,
    fill: PERSONA_COLORS[p.persona] ?? "#888",
  }));

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Customer Segmentation</h1>
          <p className="text-muted-foreground">ML-powered persona clusters & strategic insights.</p>
        </div>

        {isLoading ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : data ? (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <KPICard title="Total Customers" value={overview?.total_customers?.toLocaleString()} icon={<Users className="w-5 h-5" />} />
              <KPICard title="Personas" value={overview?.persona_count} icon={<Layers className="w-5 h-5" />} />
              <KPICard title="Silhouette Score" value={overview?.silhouette_score?.toFixed(4)} icon={<TrendingUp className="w-5 h-5" />} />
              <KPICard title="Active Clusters" value={`${overview?.cluster_count ?? 3} Clusters`} icon={<Target className="w-5 h-5" />} />
            </div>

            {/* PCA Scatter Plot */}
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Customer Cluster Map (PCA Projection)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={500}>
                  <ScatterChart margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="pc1" stroke="rgba(255,255,255,0.3)" tick={false} />
                    <YAxis dataKey="pc2" stroke="rgba(255,255,255,0.3)" tick={false} />
                    <Tooltip
                      contentStyle={{ background: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                      formatter={(value: any, name: any) => [value?.toFixed(3), name === "pc1" ? "PC1" : "PC2"]}
                      labelFormatter={(label: any) => `Cluster: ${label?.persona ?? "N/A"}`}
                    />
                    {Object.entries(PERSONA_COLORS).map(([persona, color]) => {
                      const pts = pcaPoints.filter((p: any) => p.persona === persona);
                      return pts.length > 0 ? (
                        <Scatter key={persona} name={persona} data={pts} fill={color} opacity={0.5} />
                      ) : null;
                    })}
                    <Legend />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Cluster Profiles */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {clusters.map((c: any) => (
                <Card key={c.cluster_id} className="glass-card">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: PERSONA_COLORS[c.persona] ?? "#888" }} />
                      {c.persona}
                    </CardTitle>
                    <Badge variant="outline">Cluster {c.cluster_id}</Badge>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground text-xs">Customers</p>
                        <p className="text-lg font-bold">{c.customer_count?.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">Revenue Share</p>
                        <p className="text-lg font-bold">{c.revenue_share_pct}%</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">Avg Revenue</p>
                        <p className="text-lg font-bold">R$ {c.avg_revenue?.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground text-xs">Avg Recency</p>
                        <p className="text-lg font-bold">{Math.round(c.avg_recency_days)} days</p>
                      </div>
                    </div>
                    <div className="mt-4 space-y-2 text-xs">
                      <p><span className="text-muted-foreground">Marketing:</span> {c.marketing_strategy}</p>
                      <p><span className="text-muted-foreground">Discount:</span> {c.discount_strategy}</p>
                      <p><span className="text-muted-foreground">Retention:</span> {c.retention_strategy}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Persona Revenue & Customer Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Revenue by Persona</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie data={revenueByPersona} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, value }: any) => `${name}: R$ ${(value / 1000).toFixed(0)}K`}>
                        {revenueByPersona.map((entry: any, idx: number) => (
                          <Cell key={idx} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Customers by Persona</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={customerByPersona} margin={{ top: 10, right: 10, bottom: 30, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" angle={-15} textAnchor="end" fontSize={11} />
                      <YAxis stroke="rgba(255,255,255,0.3)" />
                      <Tooltip
                        contentStyle={{ background: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {customerByPersona.map((entry: any, idx: number) => (
                          <Cell key={idx} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Strategy Insights */}
            <Widget>
              <WidgetHeader title="Strategic Recommendations" />
              <WidgetBody>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {personas.map((p: any) => (
                    <InsightCard
                      key={p.persona}
                      observation={p.persona}
                      cause={p.description}
                      recommendation={p.marketing_strategy}
                    />
                  ))}
                </div>
              </WidgetBody>
            </Widget>

            {/* Customer Lookup */}
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  Customer Lookup
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-3 mb-4">
                  <input
                    type="text"
                    placeholder="Enter customer ID (e.g., 8d50f...)"
                    value={searchId}
                    onChange={(e) => setSearchId(e.target.value)}
                    className="flex-1 px-4 py-2 rounded-lg bg-black/20 border border-border/50 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                  <button
                    onClick={() => setLookupId(searchId.trim())}
                    className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
                  >
                    <User className="w-4 h-4 inline mr-1" />
                    Lookup
                  </button>
                </div>

                {customerLoading && <p className="text-sm text-muted-foreground">Loading customer profile...</p>}

                {customerData && !customerLoading && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Persona</p>
                      <Badge className="mt-1" style={{ backgroundColor: PERSONA_COLORS[customerData.persona] ?? "#888" }}>
                        {customerData.persona}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Cluster ID</p>
                      <p className="text-sm font-semibold">{customerData.cluster_id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Confidence</p>
                      <p className="text-sm font-semibold">{(customerData.confidence_score * 100).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Total Revenue</p>
                      <p className="text-sm font-semibold">R$ {customerData.total_revenue?.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Total Orders</p>
                      <p className="text-sm font-semibold">{customerData.total_orders}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs text-muted-foreground">Purchased Categories</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {customerData.purchased_categories?.map((cat: string) => (
                          <Badge key={cat} variant="outline" className="text-xs">{cat}</Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {lookupId && !customerLoading && !customerData && (
                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                    Customer ID <strong>{lookupId}</strong> not found in demo index. Try sample ID: <code className="bg-black/30 px-1 py-0.5 rounded">4c93744516667ad3b8f1fb645a3116a4</code> (VIP Loyalist).
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="h-[400px] rounded-xl bg-card/40 border border-border/50 flex items-center justify-center">
            <p className="text-muted-foreground">Failed to load segmentation data.</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
