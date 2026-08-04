"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Widget, WidgetHeader, WidgetBody } from "@/components/ui/widget";
import { TrendingUp, DollarSign, BarChart3, Target, Sliders, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { useState, useMemo } from "react";
import { classifyDrift, driftBorderClass, driftDotColor, zScoreTone } from "@/lib/drift";
import {
  Area, AreaChart, BarChart, Bar, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis, Legend, ComposedChart,
} from "recharts";

export default function ForecastingPage() {
  const { filters } = useAppStore();
  // Dynamic Forecasting Controls
  const [horizonMonths, setHorizonMonths] = useState<number>(3);
  const [growthScenario, setGrowthScenario] = useState<number>(0); // percentage change e.g. -15, 0, 10, 25

  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading } = useQuery({
    queryKey: ["forecasting", filters],
    queryFn: () => fetcher<any>(`/forecasting/overview${queryString}`),
  });

  const { data: drift } = useQuery({
    queryKey: ["forecasting-drift"],
    queryFn: () => fetcher<any>("/forecasting/drift"),
  });

  const meta = data?.metadata;
  const monthly = data?.monthly ?? [];
  const dailyTest = data?.daily_test ?? [];
  const dailyForecast = data?.daily_forecast ?? [];
  const topFeatures = data?.top_features ?? [];

  // Dynamically generated horizon & scenario revenue forecasts
  const dynamicForecastData = useMemo(() => {
    if (!monthly.length) return { monthlyChartData: [], forecastMonths: [] };

    // Get historical months with valid revenue (> R$ 10,000)
    const validHistory = monthly.filter((m: any) => m.actual_revenue != null && m.actual_revenue > 10000);
    const historyMonths = monthly.filter((m: any) => m.actual_revenue != null && m.actual_revenue > 0);
    const baseForecastMonths = monthly.filter((m: any) => m.forecast_revenue != null);

    const scalingFactor = meta?.scaling_factor ?? 6.85;
    const baselineRev = meta?.baseline_revenue ?? 1003308;
    const lastHist = validHistory.slice(-1)[0];
    const lastRev = lastHist?.actual_revenue ?? baselineRev;

    const projectedForecast: any[] = [];
    const multiplier = 1 + growthScenario / 100;

    for (let i = 0; i < horizonMonths; i++) {
      let baseValue: number;
      let monthLabel: string;

      if (i < baseForecastMonths.length && baseForecastMonths[i].forecast_revenue != null) {
        const rawFc = baseForecastMonths[i].forecast_revenue;
        baseValue = rawFc < 1000 ? lastRev * (rawFc / scalingFactor) : rawFc;
        monthLabel = baseForecastMonths[i].month_year;
      } else {
        // Extend beyond pre-computed months dynamically
        const prevValue = projectedForecast[i - 1]?.forecast_revenue ?? lastRev;
        const seasonalFactor = i % 2 === 0 ? 1.02 : 0.99;
        baseValue = prevValue * seasonalFactor;

        const prevMonthStr = projectedForecast[i - 1]?.month_year ?? "2018-08";
        const [yr, mo] = prevMonthStr.split("-").map(Number);
        const nextDate = new Date(yr, mo, 1);
        const nextYr = nextDate.getFullYear();
        const nextMo = String(nextDate.getMonth() + 1).padStart(2, "0");
        monthLabel = `${nextYr}-${nextMo}`;
      }

      projectedForecast.push({
        month_year: monthLabel,
        forecast_revenue: Math.round(baseValue * multiplier),
      });
    }

    // Combine history + dynamic forecast for monthly chart
    const combinedChartData = historyMonths.map((m: any) => ({
      name: m.month_year,
      Revenue: m.actual_revenue,
      Forecast: null,
    }));

    projectedForecast.forEach((f: any) => {
      combinedChartData.push({
        name: f.month_year,
        Revenue: null,
        Forecast: f.forecast_revenue,
      });
    });

    return {
      monthlyChartData: combinedChartData,
      forecastMonths: projectedForecast,
    };
  }, [monthly, horizonMonths, growthScenario]);

  // Daily test chart data
  const dailyChartData = dailyTest.map((d: any) => ({
    date: d.order_date?.slice(0, 10),
    actual: d.actual_revenue,
    predicted: d.predicted_revenue,
    lower: d.forecast_lower,
    upper: d.forecast_upper,
  }));

  // Feature importance for chart with enlarged text formatting
  const featureChartData = topFeatures.slice(0, 10).map((f: any) => ({
    name: f.feature.replace(/_/g, " "),
    gain: Math.round(f.importance_gain),
  }));

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-outfit font-bold tracking-tight">Revenue Forecasting</h1>
            <p className="text-muted-foreground">RandomForest predictive engine with dynamic multi-horizon scenario modeling.</p>
          </div>
        </div>

        {isLoading ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : data ? (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard title="Model R² Accuracy" value={meta?.metrics?.test_r2 != null ? `${(meta.metrics.test_r2 * 100).toFixed(1)}%` : "N/A"} icon={<Target className="w-5 h-5" />} />
              <KPICard title="Test MAE (Mean Abs Error)" value={meta?.metrics?.test_mae != null ? `R$ ${meta.metrics.test_mae.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "N/A"} icon={<DollarSign className="w-5 h-5" />} />
              <KPICard title="Test MAPE (Avg % Error)" value={meta?.metrics?.test_mape != null ? `${meta.metrics.test_mape.toFixed(1)}%` : "N/A"} icon={<BarChart3 className="w-5 h-5" />} />
              <KPICard title="Predictive Features" value={meta?.features != null ? `${meta.features} Variables` : "N/A"} icon={<TrendingUp className="w-5 h-5 text-primary" />} />
            </div>

            {/* Dynamic Forecast Options Bar */}
            <Card className="glass-card border-primary/30 bg-primary/5">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2 text-primary">
                  <Sliders className="w-5 h-5" />
                  Dynamic Forecast Controls & Scenario Modeling
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Forecast Horizon Selector */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">
                      Forecast Horizon
                    </label>
                    <div className="flex items-center gap-2">
                      {[3, 6, 12].map((months) => (
                        <button
                          key={months}
                          onClick={() => setHorizonMonths(months)}
                          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                            horizonMonths === months
                              ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                              : "bg-black/30 hover:bg-black/50 text-muted-foreground border border-border/40"
                          }`}
                        >
                          {months} Months Outlook
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Growth Scenario Multiplier */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-semibold text-foreground/80 uppercase tracking-wider">
                        Growth Scenario Adjustment
                      </label>
                      <span className="text-xs font-mono text-primary font-bold">
                        {growthScenario > 0 ? `+${growthScenario}%` : `${growthScenario}%`}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {[-15, 0, 10, 25].map((scenario) => (
                        <button
                          key={scenario}
                          onClick={() => setGrowthScenario(scenario)}
                          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                            growthScenario === scenario
                              ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                              : "bg-black/30 hover:bg-black/50 text-muted-foreground border border-border/40"
                          }`}
                        >
                          {scenario === 0 ? "Baseline" : scenario > 0 ? `+${scenario}%` : `${scenario}%`}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Monthly Revenue: Actual + Dynamic Forecast with Purple Predicted Bars */}
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Monthly Revenue — Actual & Dynamic Forecast</span>
                  <span className="text-xs font-normal text-muted-foreground flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    Simulating {horizonMonths}-Month Outlook ({growthScenario >= 0 ? `+${growthScenario}%` : `${growthScenario}%`})
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={dynamicForecastData.monthlyChartData} margin={{ top: 10, right: 20, bottom: 40, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" angle={-45} textAnchor="end" fontSize={11} />
                    <YAxis stroke="rgba(255,255,255,0.4)" tickFormatter={(v: number) => `R$${(v / 1000).toFixed(0)}K`} />
                    <Tooltip
                      contentStyle={{ background: "rgba(0,0,0,0.85)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8 }}
                      formatter={(value: any) => [value != null ? `R$ ${value.toLocaleString()}` : "N/A", undefined]}
                    />
                    <Legend />
                    <Bar dataKey="Revenue" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Actual Revenue" />
                    <Bar dataKey="Forecast" fill="#a78bfa" radius={[4, 4, 0, 0]} name="Predicted Revenue (Forecast)" />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Dynamic Forecast Month Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {dynamicForecastData.forecastMonths.map((m: any) => (
                <Card key={m.month_year} className="glass-card border-primary/20 hover:border-primary/40 transition-colors">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{m.month_year}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold font-outfit text-[#a78bfa]">R$ {m.forecast_revenue?.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground mt-1">Projected Revenue</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Daily Test: Actual vs Predicted */}
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Daily Revenue — Actual vs Predicted (Test Period)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={dailyChartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="date" stroke="rgba(255,255,255,0.4)" tick={false} />
                    <YAxis stroke="rgba(255,255,255,0.4)" tickFormatter={(v: number) => `R$${(v / 1000).toFixed(0)}K`} />
                    <Tooltip
                      contentStyle={{ background: "rgba(0,0,0,0.85)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8 }}
                      formatter={(value: any) => [value != null ? `R$ ${value.toLocaleString()}` : "N/A", undefined]}
                    />
                    <Legend />
                    <Area type="monotone" dataKey={["lower", "upper"] as any} stroke="none" fill="#a78bfa" fillOpacity={0.12} name="90% Interval" />
                    <Area type="monotone" dataKey="actual" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} name="Actual" />
                    <Area type="monotone" dataKey="predicted" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.2} name="Predicted" />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Feature Importance with Large Readable Text */}
            <Widget>
              <WidgetHeader title="Top Predictive Features (Feature Importance)" />
              <WidgetBody>
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart data={featureChartData} layout="vertical" margin={{ top: 10, right: 30, bottom: 10, left: 180 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis type="number" stroke="rgba(255,255,255,0.6)" tick={{ fill: "#cbd5e1", fontSize: 13, fontWeight: 500 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: "#f1f5f9", fontSize: 14, fontWeight: 600 }}
                      width={170}
                    />
                    <Tooltip
                      contentStyle={{ background: "rgba(0,0,0,0.9)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8, color: "#fff" }}
                      formatter={(value: any) => [`Gain: ${value?.toLocaleString()}`, "Importance Gain"]}
                    />
                    <Bar dataKey="gain" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </WidgetBody>
            </Widget>

            {/* Model Drift Check */}
            {drift && (() => {
              const driftStatus = classifyDrift(drift);
              return (
              <Card className={`glass-card ${driftBorderClass(driftStatus)}`}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: driftDotColor(driftStatus) }} />
                    Model Drift Check
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                    <span className="font-semibold capitalize">{driftStatus === "unavailable" ? "Unavailable" : driftStatus}</span>
                    <span className="text-muted-foreground">Max shift: <span className="font-mono text-foreground">{drift.score}</span> (threshold {drift.drift_threshold})</span>
                    <span className="text-muted-foreground">{drift.n_drifted} of {drift.n_features} features drifted</span>
                    {drift.trained_on && <span className="text-muted-foreground">Trained {drift.trained_on} · {drift.training_rows} rows</span>}
                  </div>
                  <p className="text-sm text-muted-foreground">{drift.message}</p>
                  {drift.drifted_features?.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1">
                      {drift.drifted_features.slice(0, 6).map((f: any) => (
                        <div key={f.feature} className="flex items-center justify-between rounded-lg bg-black/30 border border-border/40 px-3 py-2 text-xs">
                          <span className="font-medium text-foreground/90">{f.feature.replace(/_/g, " ")}</span>
                          <span className={`font-mono ${zScoreTone(f.z_score)}`}>
                            z={f.z_score > 0 ? "+" : ""}{f.z_score}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              );
            })()}
          </>
        ) : (
          <div className="h-[400px] rounded-xl bg-card/40 border border-border/50 flex items-center justify-center">
            <p className="text-muted-foreground">Failed to load forecast data.</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
