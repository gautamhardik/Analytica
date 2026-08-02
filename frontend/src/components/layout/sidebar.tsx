"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, LineChart, Users, ShoppingBag, Map, FileText, Settings, Sparkles, Layers, TrendingUp, X } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { name: "Executive Workspace", href: "/", icon: LayoutDashboard },
  { name: "Revenue Workspace", href: "/sales", icon: LineChart },
  { name: "Customer Workspace", href: "/customers", icon: Users },
  { name: "Product Workspace", href: "/products", icon: ShoppingBag },
  { name: "Geography Workspace", href: "/geography", icon: Map },
  { name: "Segment Workspace", href: "/segmentation", icon: Layers },
  { name: "Forecast Workspace", href: "/forecasting", icon: TrendingUp },
  { name: "Executive Summary", href: "/executive-summary", icon: Sparkles },
  { name: "Reports Workspace", href: "/reports", icon: FileText },
  { name: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  onItemClick?: () => void;
  onCloseMobile?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ onItemClick, onCloseMobile, isMobile }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside aria-label="Main navigation" className={cn(
      "border-r border-border/50 bg-card/30 backdrop-blur-xl flex flex-col h-full sticky top-0 z-40",
      isMobile ? "w-full border-r-0" : "hidden md:flex w-64"
    )}>
      <div className="h-16 flex items-center justify-between px-6 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 flex items-center justify-center shadow-md shadow-amber-500/20">
            <LineChart className="w-4 h-4 text-black font-bold" />
          </div>
          <span className="font-outfit font-bold text-xl tracking-tight text-foreground">Analytica</span>
        </div>

        {isMobile && (
          <button onClick={onCloseMobile} className="p-1 rounded text-muted-foreground hover:text-foreground md:hidden">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-4 flex flex-col gap-1.5">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={onItemClick}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group",
                isActive
                  ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-xs font-semibold"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-amber-400 shadow-xs shadow-amber-400" />
              )}
              <Icon className={cn("w-4 h-4 transition-transform duration-200 group-hover:scale-110", isActive ? "text-amber-400" : "text-slate-400 group-hover:text-amber-300")} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>


    </aside>
  );
}
