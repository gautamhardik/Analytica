"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { Sparkles, TrendingUp, AlertTriangle, Info, Map as MapIcon, Users, ShoppingBag, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";

export default function InsightsPage() {
  const { filters } = useAppStore();

  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["insights_all", filters],
    queryFn: () => fetcher<any>(`/insights${queryString}`),
  });

  const insights = data?.insights || [];

  const getDomainIcon = (domain: string) => {
    switch (domain?.toLowerCase()) {
      case "sales": return DollarSign;
      case "customers": return Users;
      case "products": return ShoppingBag;
      case "geography": return MapIcon;
      default: return TrendingUp;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "positive": return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
      case "warning": return "text-amber-500 bg-amber-500/10 border-amber-500/20";
      case "critical": return "text-destructive bg-destructive/10 border-destructive/20";
      default: return "text-primary bg-primary/10 border-primary/20";
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "positive": return <TrendingUp className="w-5 h-5" />;
      case "warning": return <AlertTriangle className="w-5 h-5" />;
      case "critical": return <AlertTriangle className="w-5 h-5" />;
      default: return <Info className="w-5 h-5" />;
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            Business Insights
          </h1>
          <p className="text-muted-foreground">Auto-generated metrics from the data warehouse engine.</p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-36 rounded-xl bg-card/40 animate-pulse border border-border/50" />
            ))}
          </div>
        ) : error ? (
          <div className="p-6 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            Failed to load insights. Please check backend server.
          </div>
        ) : insights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {insights.map((insight: any, i: number) => {
              const DomainIcon = getDomainIcon(insight.domain);
              const colorClasses = getSeverityColor(insight.severity).split(" ");
              
              return (
                <Card key={i} className={cn("glass-card border-l-4 transition-all hover:-translate-y-1 shadow-md", colorClasses[2])}>
                  <CardHeader className="pb-2 flex flex-row items-start justify-between space-y-0">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-black/20 text-muted-foreground">
                        <DomainIcon className="w-4 h-4" />
                      </div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{insight.domain}</span>
                    </div>
                    <div className={cn("p-1.5 rounded-full", `${colorClasses[0]} ${colorClasses[1]}`)}>
                      {getSeverityIcon(insight.severity)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardTitle className="text-base font-semibold leading-snug mb-1.5">{insight.title}</CardTitle>
                    <p className="text-xs text-muted-foreground leading-relaxed">{insight.detail}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <div className="p-12 text-center border border-dashed border-border/50 rounded-xl bg-card/20 text-muted-foreground">
            No intelligence rules triggered for current filter criteria.
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
