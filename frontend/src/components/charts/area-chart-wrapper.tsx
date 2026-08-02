"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";

const AreaChart = dynamic(
  () => import("recharts").then((m) => m.AreaChart),
  { ssr: false }
);
const Area = dynamic(
  () => import("recharts").then((m) => m.Area),
  { ssr: false }
);
const CartesianGrid = dynamic(
  () => import("recharts").then((m) => m.CartesianGrid),
  { ssr: false }
);
const ResponsiveContainer = dynamic(
  () => import("recharts").then((m) => m.ResponsiveContainer),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import("recharts").then((m) => m.Tooltip),
  { ssr: false }
);
const XAxis = dynamic(
  () => import("recharts").then((m) => m.XAxis),
  { ssr: false }
);
const YAxis = dynamic(
  () => import("recharts").then((m) => m.YAxis),
  { ssr: false }
);

export interface AreaChartWrapperProps {
  data: any[];
  xKey: string;
  yKey: string;
  xFormatter?: (value: any) => string;
  yFormatter?: (value: any) => string;
  tooltipFormatter?: (value: any) => [string, string];
  gradientId?: string;
  gradientColor?: string;
  strokeColor?: string;
  height?: number;
}

export function AreaChartWrapper({
  data,
  xKey,
  yKey,
  xFormatter,
  yFormatter,
  tooltipFormatter,
  gradientId = "areaGradient",
  gradientColor = "var(--primary)",
  strokeColor = "var(--primary)",
  height = 320,
}: AreaChartWrapperProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={gradientColor} stopOpacity={0.4} />
              <stop offset="95%" stopColor={gradientColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey={xKey} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} tickFormatter={xFormatter} />
          <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} tickFormatter={yFormatter} />
          <Tooltip contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "8px" }} formatter={tooltipFormatter} />
          <Area type="monotone" dataKey={yKey} stroke={strokeColor} strokeWidth={2.5} fillOpacity={1} fill={`url(#${gradientId})`} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
