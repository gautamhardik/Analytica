"use client";

import { useEffect, Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { FilterX, Save, Calendar, MapPin, Tag, User } from "lucide-react";
import { cn, formatMonthYear, formatStateName, getMonthLabel, getStateLabel, getCategoryLabel, getSegmentLabel } from "@/lib/utils";

function FilterBarContent() {
  const searchParams = useSearchParams();
  const { filters, setFilter, resetFilters } = useAppStore();

  const { data: filterOptions } = useQuery<{ months: string[]; states: string[]; categories: string[] }>({
    queryKey: ["filterOptions"],
    queryFn: () => fetcher("/filters"),
  });

  const months = filterOptions?.months
  const sortedMonths = useMemo(() => {
    if (!months) return []
    return [...months].sort()
  }, [months])

  // Sync from URL to Store on mount
  useEffect(() => {
    const month = searchParams.get("month");
    const state = searchParams.get("state");
    const category = searchParams.get("category");
    const segment = searchParams.get("segment");

    if (month) setFilter("month", month);
    if (state) setFilter("state", state);
    if (category) setFilter("category", category);
    if (segment) setFilter("segment", segment);
  }, [searchParams, setFilter]);

  // Sync from Store to URL
  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    
    let hasChanges = false;
    Object.entries(filters).forEach(([key, value]) => {
      if (value && value !== "all" && value !== "all_time") {
        if (params.get(key) !== value) {
          params.set(key, value);
          hasChanges = true;
        }
      } else {
        if (params.has(key)) {
          params.delete(key);
          hasChanges = true;
        }
      }
    });

    const newUrl = `?${params.toString()}`;
    if (hasChanges && params.toString() !== searchParams.toString()) {
      window.history.replaceState(null, '', newUrl);
    }
  }, [filters, searchParams]);

  const hasActiveFilters = Object.values(filters).some(val => val !== null && val !== "all" && val !== "all_time");

  return (
    <div className="w-full bg-card/80 backdrop-blur-md border-b border-border/50 px-4 sm:px-6 py-2 sticky top-16 z-20 flex flex-col sm:flex-row items-center gap-4 justify-between">
      <div className="flex flex-wrap items-center gap-3 w-full">
        
        {/* Date Filter */}
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-muted-foreground hidden sm:block" />
          <Select value={filters.month || "all"} onValueChange={(val) => setFilter("month", val)}>
            <SelectTrigger className="w-[180px] h-9 bg-white/5 dark:bg-black/20 border-border/60 text-sm focus:ring-1 focus:ring-primary/50 hover:border-primary/30 transition-colors">
              <span className="truncate">{getMonthLabel(filters.month)}</span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="font-medium">All Time</span>
              </SelectItem>
              {sortedMonths.map((m: string) => (
                <SelectItem key={m} value={m}>{formatMonthYear(m)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Region Filter */}
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-muted-foreground hidden sm:block" />
          <Select value={filters.state || "all"} onValueChange={(val) => setFilter("state", val)}>
            <SelectTrigger className="w-[190px] h-9 bg-white/5 dark:bg-black/20 border-border/60 text-sm focus:ring-1 focus:ring-primary/50 hover:border-primary/30 transition-colors">
              <span className="truncate">{getStateLabel(filters.state)}</span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="font-medium">All States</span>
              </SelectItem>
              {filterOptions?.states?.map((s: string) => (
                <SelectItem key={s} value={s}>
                  <span>{formatStateName(s)}</span>
                  <span className="text-muted-foreground/60 ml-1 text-xs">({s})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-muted-foreground hidden sm:block" />
          <Select value={filters.category || "all"} onValueChange={(val) => setFilter("category", val)}>
            <SelectTrigger className="w-[190px] h-9 bg-white/5 dark:bg-black/20 border-border/60 text-sm focus:ring-1 focus:ring-primary/50 hover:border-primary/30 transition-colors">
              <span className="truncate">{getCategoryLabel(filters.category)}</span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="font-medium">All Categories</span>
              </SelectItem>
              {filterOptions?.categories?.map((c: string) => (
                <SelectItem key={c} value={c}>
                  <span className="capitalize">{c.replace(/_/g, " ")}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Customer Segment */}
        <div className="flex items-center gap-2">
          <User className="w-4 h-4 text-muted-foreground hidden sm:block" />
          <Select value={filters.segment || "all"} onValueChange={(val) => setFilter("segment", val)}>
            <SelectTrigger className="w-[175px] h-9 bg-white/5 dark:bg-black/20 border-border/60 text-sm focus:ring-1 focus:ring-primary/50 hover:border-primary/30 transition-colors">
              <span className="truncate">{getSegmentLabel(filters.segment)}</span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="font-medium">All Segments</span>
              </SelectItem>
              <SelectItem value="new">New Customers</SelectItem>
              <SelectItem value="repeat">Repeat Buyers</SelectItem>
              <SelectItem value="vip">VIP (High LTV)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Filter Actions */}
      <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={resetFilters}
          title={hasActiveFilters ? "Reset all active filters to default state" : "No active filters applied"}
          disabled={!hasActiveFilters}
          className={cn(
            "h-9 px-3 text-xs transition-all active:scale-95 cursor-pointer",
            hasActiveFilters 
              ? "opacity-100 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 border border-rose-500/20" 
              : "opacity-40 cursor-not-allowed border border-transparent"
          )}
        >
          <FilterX className="w-3.5 h-3.5 mr-1.5" />
          Reset
        </Button>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => {
            try {
              window.localStorage.setItem("analytica_saved_view", JSON.stringify(filters));
              (window as any).__analytica_toast?.push?.("Current filter view saved.", "success");
            } catch (e) {
              (window as any).__analytica_toast?.push?.("Failed to save view.", "error");
            }
          }}
          className="h-9 px-3 text-xs bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25 active:scale-95 transition-all shadow-xs cursor-pointer"
        >
          <Save className="w-3.5 h-3.5 mr-1.5" />
          Save View
        </Button>
      </div>
    </div>
  );
}

export function GlobalFilterBar() {
  return (
    <Suspense fallback={<div className="h-12 w-full bg-card/80 border-b border-border/50"></div>}>
      <FilterBarContent />
    </Suspense>
  )
}
