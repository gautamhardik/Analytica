import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownIcon, ArrowUpIcon, MinusIcon } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number | null;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
  sparklineData?: number[];
  className?: string;
}

export function KPICard({ title, value, change, trend, icon, sparklineData, className }: KPICardProps) {
  // Generate SVG path for sparkline if data exists or default decorative wave
  const points = sparklineData && sparklineData.length > 1
    ? sparklineData
    : trend === "up" ? [20, 35, 25, 45, 40, 60, 55, 75]
    : trend === "down" ? [75, 60, 65, 40, 45, 30, 20, 15]
    : [40, 42, 38, 45, 42, 44, 40, 43];

  const min = Math.min(...points);
  const max = Math.max(...points) || 1;
  const range = max - min || 1;

  const svgPoints = points
    .map((val, idx) => {
      const x = (idx / (points.length - 1)) * 120;
      const y = 40 - ((val - min) / range) * 30;
      return `${x},${y}`;
    })
    .join(" ");

  const strokeColor = trend === "up" ? "rgba(16, 185, 129, 0.45)" : trend === "down" ? "rgba(244, 63, 94, 0.45)" : "rgba(245, 158, 11, 0.35)";
  const fillColor = trend === "up" ? "rgba(16, 185, 129, 0.08)" : trend === "down" ? "rgba(244, 63, 94, 0.08)" : "rgba(245, 158, 11, 0.08)";

  return (
    <Card className={cn(
      "glass-card overflow-hidden relative group border border-white/10 hover:border-amber-500/40 transition-all duration-200 ease-out active:scale-[0.995]",
      className
    )}>
      <CardContent className="p-6">
        <div className="flex justify-between items-start relative z-10">
          <div className="space-y-2 min-h-[72px] flex flex-col justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 group-hover:text-slate-300 transition-colors">{title}</p>
            <div className="flex items-baseline gap-2">
              <h2 className="text-xl sm:text-2xl font-outfit font-extrabold tracking-tight whitespace-nowrap text-foreground">
                {value}
              </h2>
            </div>
            
            {change !== undefined && change !== null ? (
              <div className="flex items-center gap-1.5 mt-1">
                <div
                  className={cn(
                    "flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full border shadow-xs transition-colors",
                    trend === "up" && "bg-emerald-500/15 text-emerald-400 border-emerald-500/35",
                    trend === "down" && "bg-rose-500/15 text-rose-400 border-rose-500/35",
                    trend === "neutral" && "bg-slate-800/80 text-slate-300 border-slate-700"
                  )}
                >
                  {trend === "up" && <ArrowUpIcon className="w-3 h-3 mr-0.5" />}
                  {trend === "down" && <ArrowDownIcon className="w-3 h-3 mr-0.5" />}
                  {trend === "neutral" && <MinusIcon className="w-3 h-3 mr-0.5" />}
                  {Math.abs(change)}%
                </div>
                <span className="text-[11px] font-medium text-slate-400">vs last period</span>
              </div>
            ) : (
              <div className="h-5" />
            )}
          </div>
          {icon && (
            <div className="p-3 bg-amber-500/10 rounded-xl text-amber-400 border border-amber-500/20 group-hover:scale-105 group-hover:bg-amber-500/20 transition-all">
              {icon}
            </div>
          )}
        </div>
        
        {/* Sparkline background SVG */}
        <div className="absolute bottom-0 right-0 left-0 h-12 pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity">
          <svg className="w-full h-full" viewBox="0 0 120 40" preserveAspectRatio="none">
            <polygon points={`0,40 ${svgPoints} 120,40`} fill={fillColor} />
            <polyline points={svgPoints} fill="none" stroke={strokeColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        {/* Subtle glow effect behind the card content */}
        <div className="absolute -top-12 -right-12 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-amber-500/20 transition-colors" />
      </CardContent>
    </Card>
  );
}
