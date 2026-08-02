"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";

const BarChart = dynamic(
  () => import("recharts").then((m) => m.BarChart),
  { ssr: false }
);
const Bar = dynamic(
  () => import("recharts").then((m) => m.Bar),
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

export interface BarChartWrapperProps {
  data: any[];
  xKey: string;
  yKey: string;
  xFormatter?: (value: any) => string;
  yFormatter?: (value: any) => string;
  tooltipFormatter?: (value: any) => [string, string];
  labelFormatter?: (value: any) => string;
  barSize?: number;
  gradientId?: string;
  gradientStart?: string;
  gradientEnd?: string;
  height?: number;
  onClick?: (data: any) => void;
}

export function BarChartWrapper({
  data,
  xKey,
  yKey,
  xFormatter,
  yFormatter,
  tooltipFormatter,
  labelFormatter,
  barSize = 42,
  gradientId = "barGradient",
  gradientStart = "#f59e0b",
  gradientEnd = "#d97706",
  height = 320,
  onClick,
}: BarChartWrapperProps) {
  return (
    <div style={{ width: "100%", height, minHeight: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} onClick={onClick}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={gradientStart} stopOpacity={1} />
              <stop offset="100%" stopColor={gradientEnd} stopOpacity={0.6} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey={xKey} stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={xFormatter} />
          <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={yFormatter} />
          <Tooltip contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "8px" }} formatter={tooltipFormatter} labelFormatter={labelFormatter} />
          <Bar dataKey={yKey} fill={`url(#${gradientId})`} radius={[6, 6, 0, 0]} barSize={barSize} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
