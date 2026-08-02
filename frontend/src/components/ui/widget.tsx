"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Download, RefreshCw, MoreVertical, Maximize2 } from "lucide-react";
import { Button } from "./button";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from "./dropdown-menu";

const Widget = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "glass-card border border-white/10 text-card-foreground shadow-lg flex flex-col overflow-hidden relative group transition-all duration-300 hover:shadow-2xl hover:border-amber-500/30",
        className
      )}
      {...props}
    />
  )
);
Widget.displayName = "Widget";

const WidgetHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { title: string; subtitle?: string; onRefresh?: () => void }>(
  ({ className, title, subtitle, onRefresh, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-start justify-between p-5 sm:p-6 pb-2", className)}
      {...props}
    >
      <div className="flex flex-col space-y-1">
        <h3 className="font-outfit font-bold tracking-tight text-base sm:text-lg text-foreground flex items-center gap-2">
          {title}
        </h3>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-1 opacity-70 group-hover:opacity-100 transition-opacity">
        {onRefresh && (
          <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/10" onClick={onRefresh}>
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground hover:text-amber-400 transition-colors" />
          </Button>
        )}
        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/10">
          <Maximize2 className="h-3.5 w-3.5 text-muted-foreground hover:text-amber-400 transition-colors" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none hover:bg-white/10 h-8 w-8">
            <MoreVertical className="h-3.5 w-3.5 text-muted-foreground" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bg-card/95 border-white/10 backdrop-blur-xl">
            <DropdownMenuItem className="cursor-pointer text-xs"><Download className="mr-2 h-3.5 w-3.5 text-amber-400" /> Export CSV</DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer text-xs"><Download className="mr-2 h-3.5 w-3.5 text-amber-400" /> Export PNG</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
);
WidgetHeader.displayName = "WidgetHeader";

const WidgetBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-5 sm:p-6 pt-2 flex-1 relative min-h-[160px]", className)} {...props} />
  )
);
WidgetBody.displayName = "WidgetBody";

const WidgetInsights = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("border-t border-white/10 bg-black/20 p-4 sm:p-5 text-xs text-muted-foreground flex items-center gap-2", className)}
      {...props}
    />
  )
);
WidgetInsights.displayName = "WidgetInsights";

const WidgetActions = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-center p-5 sm:p-6 pt-0 mt-auto", className)}
      {...props}
    />
  )
);
WidgetActions.displayName = "WidgetActions";

export { Widget, WidgetHeader, WidgetBody, WidgetInsights, WidgetActions };
