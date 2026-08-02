"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Lightbulb, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { Button } from "./button";

interface InsightCardProps {
  observation: string;
  cause?: string;
  impact?: string;
  recommendation?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
  onActionClick?: () => void;
}

export function InsightCard({
  observation,
  cause,
  impact,
  recommendation,
  trend = "neutral",
  className,
  onActionClick
}: InsightCardProps) {
  return (
    <div className={cn("rounded-lg border border-primary/20 bg-primary/5 p-4 space-y-3", className)}>
      <div className="flex items-start gap-3">
        <div className={cn(
          "p-2 rounded-full mt-0.5",
          trend === "up" ? "bg-emerald-500/20 text-emerald-500" :
          trend === "down" ? "bg-destructive/20 text-destructive" :
          "bg-primary/20 text-primary"
        )}>
          {trend === "up" ? <TrendingUp className="w-4 h-4" /> :
           trend === "down" ? <TrendingDown className="w-4 h-4" /> :
           <Lightbulb className="w-4 h-4" />}
        </div>
        <div className="flex-1 space-y-1">
          <p className="text-sm font-semibold text-foreground leading-snug">
            {observation}
          </p>
          {cause && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground/80">Cause:</span> {cause}
            </p>
          )}
          {impact && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground/80">Impact:</span> {impact}
            </p>
          )}
          {recommendation && (
            <div className="mt-2 pt-2 border-t border-primary/10">
              <p className="text-xs text-primary font-medium">
                Recommendation: {recommendation}
              </p>
            </div>
          )}
        </div>
      </div>
      
      {onActionClick && (
        <div className="flex justify-end pt-1">
          <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 text-primary hover:text-primary hover:bg-primary/10" onClick={onActionClick}>
            Take Action <ArrowRight className="w-3 h-3" />
          </Button>
        </div>
      )}
    </div>
  );
}
