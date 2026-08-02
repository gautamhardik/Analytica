"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { Sparkles, TrendingUp, Users, ShoppingBag, MapPin, BarChart2, AlertTriangle, CheckCircle, Info, ShieldAlert, Lightbulb, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { useMemo } from "react";

const SECTION_ICONS: Record<string, React.ReactNode> = {
  "Revenue Performance": <TrendingUp className="w-5 h-5" />,
  "Customer Health": <Users className="w-5 h-5" />,
  "Product Performance": <ShoppingBag className="w-5 h-5" />,
  "Geographic Distribution": <MapPin className="w-5 h-5" />,
  "Customer Segmentation (ML)": <BarChart2 className="w-5 h-5" />,
  "Revenue Forecast": <TrendingUp className="w-5 h-5" />,
};

const SENTIMENT_META: Record<string, { label: string; badge: string; icon: React.ReactNode; glow: string }> = {
  positive: {
    label: "Positive",
    badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    icon: <CheckCircle className="w-4 h-4" />,
    glow: "shadow-emerald-500/10 border-emerald-500/30",
  },
  warning: {
    label: "Attention Needed",
    badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    icon: <AlertTriangle className="w-4 h-4" />,
    glow: "shadow-amber-500/10 border-amber-500/30",
  },
  neutral: {
    label: "Stable",
    badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    icon: <Info className="w-4 h-4" />,
    glow: "shadow-blue-500/10 border-blue-500/30",
  },
};

const SECTION_STYLES: Record<string, { card: string; badge: string; icon: React.ReactNode }> = {
  positive: {
    card: "border-emerald-500/30 bg-emerald-500/5 hover:shadow-emerald-500/10",
    badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    icon: <CheckCircle className="w-4 h-4 text-emerald-400" />,
  },
  warning: {
    card: "border-amber-500/30 bg-amber-500/5 hover:shadow-amber-500/10",
    badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
  },
  neutral: {
    card: "border-blue-500/30 bg-blue-500/5 hover:shadow-blue-500/10",
    badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    icon: <Info className="w-4 h-4 text-blue-400" />,
  },
};

const FILTER_LABELS: Record<string, string> = {
  month: "Month",
  state: "State",
  category: "Category",
  segment: "Segment",
};

export default function ExecutiveSummaryPage() {
  const { filters } = useAppStore();
  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["executive-summary", filters],
    queryFn: () => fetcher<any>(`/executive-summary${queryString}`),
  });

  const activeFilters = useMemo(
    () =>
      Object.entries(filters).filter(
        ([, v]) => v && v !== "all" && v !== "all_time"
      ),
    [filters]
  );

  const overall = data ? (SENTIMENT_META[data.overall_sentiment] ?? SENTIMENT_META.neutral) : null;

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 pb-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-outfit font-bold tracking-tight">Executive Summary</h1>
              <p className="text-muted-foreground text-sm">
                Automated business intelligence report across all analytics domains
              </p>
            </div>
          </div>

          {overall && (
            <div className={cn("flex items-center gap-2 px-3 py-2 rounded-xl border bg-card/60 shadow-md", overall.glow)}>
              <span className="text-sm font-semibold text-muted-foreground">Overall:</span>
              <span className={cn("flex items-center gap-1.5 text-sm px-2.5 py-1 rounded-full border font-medium", overall.badge)}>
                {overall.icon}
                {overall.label}
              </span>
            </div>
          )}
        </div>

        {/* Active Filters */}
        {activeFilters.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Report scoped to:</span>
            {activeFilters.map(([k, v]) => (
              <span
                key={k}
                className="text-xs font-mono px-2 py-0.5 rounded-md bg-card/60 border border-border/50 text-foreground/80"
              >
                {FILTER_LABELS[k] ?? k}: {String(v)}
              </span>
            ))}
          </div>
        )}

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-36 rounded-xl bg-card/40 animate-pulse border border-border/50" />
            ))}
          </div>
        ) : error && !data ? (
          <div className="p-6 bg-destructive/10 text-destructive rounded-xl border border-destructive/20">
            Failed to load executive summary. Please check backend server.
          </div>
        ) : data ? (
          <div className="space-y-6">
            {/* Executive Summary Block */}
            <Card className="glass-card border-primary/20 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <CardTitle className="text-base">Executive Overview</CardTitle>
                  <span className="ml-auto text-xs text-muted-foreground font-mono">
                    Generated{" "}
                    {new Date(data.generated_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-foreground/90">{data.executive_summary}</p>
              </CardContent>
            </Card>

            {/* Section Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(data.sections || []).map((section: any, idx: number) => {
                const style = SECTION_STYLES[section.sentiment] ?? SECTION_STYLES.neutral;
                return (
                  <Card
                    key={idx}
                    className={cn("glass-card transition-all hover:scale-[1.01] hover:shadow-md", style.card)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-card/50">
                            {SECTION_ICONS[section.title] ?? <BarChart2 className="w-4 h-4" />}
                          </div>
                          <CardTitle className="text-sm font-semibold">{section.title}</CardTitle>
                        </div>
                        <span className={cn("flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium capitalize", style.badge)}>
                          {style.icon}
                          {section.sentiment}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground leading-relaxed">{section.summary}</p>

                      {/* Key Metrics Pills */}
                      {section.metrics?.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {section.metrics.map((metric: string, i: number) => (
                            <span
                              key={i}
                              className="text-xs font-mono px-2 py-0.5 rounded-md bg-card/60 border border-border/50 text-foreground/80"
                            >
                              {metric}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Recommendation */}
                      {section.recommendation && (
                        <div className="flex gap-2 items-start pt-1 border-t border-border/30">
                          <Sparkles className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
                          <p className="text-xs text-primary/90 leading-relaxed">{section.recommendation}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Risks & Opportunities */}
            {(data.key_risks?.length > 0 || data.opportunities?.length > 0) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="glass-card border-rose-500/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                      <ShieldAlert className="w-4 h-4 text-rose-400" />
                      Key Risks
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {(data.key_risks || []).map((risk: string, i: number) => (
                      <div key={i} className="flex gap-2 items-start text-sm text-rose-200/90">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0" />
                        <span className="leading-relaxed">{risk}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="glass-card border-emerald-500/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                      <Lightbulb className="w-4 h-4 text-emerald-400" />
                      Opportunities
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {(data.opportunities || []).map((opp: string, i: number) => (
                      <div key={i} className="flex gap-2 items-start text-sm text-emerald-200/90">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                        <span className="leading-relaxed">{opp}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
