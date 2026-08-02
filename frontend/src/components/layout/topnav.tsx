"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Menu, ExternalLink, Check } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { LiveActivityCenter } from "@/components/ui/live-activity-center";
import { api } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";

interface TopNavProps {
  onToggleMobileSidebar?: () => void;
}

export function TopNav({ onToggleMobileSidebar }: TopNavProps) {
  const [isLive, setIsLive] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    api.get("/health", { timeout: 3000 })
      .then(r => setIsLive(r.status === 200))
      .catch(() => setIsLive(false));
  }, []);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = "search-listbox";

  // Live search query effect
  useEffect(() => {
    if (searchQuery.trim().length >= 2) {
      const timer = setTimeout(async () => {
        try {
          const res = await api.get(`/search?q=${encodeURIComponent(searchQuery)}`);
          setSearchResults(res.data.results || []);
          setSearchOpen(true);
          setActiveIndex(-1);
        } catch (e) {
          setSearchResults([]);
        }
      }, 200);
      return () => clearTimeout(timer);
    } else {
      const reset = setTimeout(() => {
        setSearchResults([]);
        setSearchOpen(false);
        setActiveIndex(-1);
      }, 0);
      return () => clearTimeout(reset);
    }
  }, [searchQuery]);

  // Close search on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="h-16 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Menu Toggle */}
        <button
          onClick={onToggleMobileSidebar}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 active:scale-95 md:hidden transition-all cursor-pointer"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Live Search — WCAG combobox */}
        <div
          ref={searchRef}
          role="combobox"
          aria-expanded={searchOpen && searchResults.length > 0}
          aria-haspopup="listbox"
          aria-controls={listboxId}
          aria-label="Global search"
          className="relative w-48 sm:w-64"
        >
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            id="global-search-input"
            type="text"
            role="searchbox"
            aria-label="Search metrics, categories..."
            aria-autocomplete="list"
            aria-controls={listboxId}
            aria-activedescendant={
              activeIndex >= 0 ? `search-option-${activeIndex}` : undefined
            }
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
            }}
            onFocus={() => searchQuery.length >= 2 && setSearchOpen(true)}
            onKeyDown={(e) => {
              if (!searchOpen || searchResults.length === 0) {
                if (e.key === "Escape") {
                  setSearchOpen(false);
                  inputRef.current?.blur();
                }
                return;
              }
              switch (e.key) {
                case "ArrowDown":
                  e.preventDefault();
                  setActiveIndex((prev) =>
                    prev < searchResults.length - 1 ? prev + 1 : 0
                  );
                  break;
                case "ArrowUp":
                  e.preventDefault();
                  setActiveIndex((prev) =>
                    prev > 0 ? prev - 1 : searchResults.length - 1
                  );
                  break;
                case "Escape":
                  e.preventDefault();
                  setSearchOpen(false);
                  setActiveIndex(-1);
                  break;
                case "Enter":
                  e.preventDefault();
                  if (activeIndex >= 0 && searchResults[activeIndex]) {
                    router.push(searchResults[activeIndex].href);
                    setSearchOpen(false);
                    setSearchQuery("");
                    setActiveIndex(-1);
                  }
                  break;
              }
            }}
            placeholder="Search metrics, categories..."
            className="h-9 w-full rounded-md border border-border/50 bg-black/20 pl-9 pr-4 text-xs sm:text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/50 transition-all"
          />

          {/* Floating Search Results Overlay */}
          {searchOpen && searchResults.length > 0 && (
            <ul
              id={listboxId}
              role="listbox"
              aria-label="Search results"
              className="absolute top-11 left-0 w-80 bg-card border border-border rounded-lg shadow-xl py-2 z-50 max-h-80 overflow-y-auto"
            >
              <li
                role="presentation"
                className="px-3 py-1 text-[10px] uppercase font-semibold text-muted-foreground tracking-wider"
              >
                Matching Search Results ({searchResults.length})
              </li>
              {searchResults.map((item, idx) => (
                <li
                  key={idx}
                  id={`search-option-${idx}`}
                  role="option"
                  aria-selected={idx === activeIndex}
                  onClick={() => {
                    router.push(item.href);
                    setSearchOpen(false);
                    setSearchQuery("");
                    setActiveIndex(-1);
                  }}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={`px-3 py-2 cursor-pointer flex items-center justify-between border-b border-border/20 last:border-0 ${
                    idx === activeIndex
                      ? "bg-primary/10"
                      : "hover:bg-white/5"
                  }`}
                >
                  <div>
                    <p className="text-xs font-medium text-foreground">
                      {item.title}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {item.category}
                    </p>
                  </div>
                  <ExternalLink className="w-3 h-3 text-muted-foreground" />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-6">
        {/* Health Indicators */}
        <div className="hidden lg:flex items-center gap-3 text-[10px] uppercase font-bold tracking-wider">
          <div className="flex items-center gap-1.5 text-primary bg-primary/15 border border-primary/30 px-2.5 py-1 rounded-md shadow-xs">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span>MODE: {isLive === null ? "CHECKING" : isLive ? "LIVE" : "DEMO / STATIC"}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-1 rounded-md shadow-xs">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>DATA WAREHOUSE: READY</span>
          </div>
        </div>

        <div className="h-4 w-px bg-border/50 hidden sm:block" />

        <div className="flex items-center gap-3">
          {/* Live Activity Drawer */}
          <Sheet>
            <SheetTrigger
              className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 cursor-pointer"
            >
              <Activity className="w-5 h-5" />
            </SheetTrigger>
            <SheetContent side="right" className="p-0 w-80 sm:w-96 border-l border-border bg-transparent">
              <LiveActivityCenter />
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
