"use client";

import { useEffect, useState } from "react";
import { Activity, ShoppingCart, AlertTriangle, ArrowUpRight, ArrowDownRight, Package } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface StreamEvent {
  id: string;
  type: "purchase" | "alert" | "update" | "stock";
  message: string;
  time: Date;
  value?: string;
  region?: string;
}

const EVENT_TEMPLATES = [
  { type: "purchase", message: "New high-value order in SP region", value: "R$ 1,250" },
  { type: "alert", message: "Drop in conversion rate detected for Electronics" },
  { type: "purchase", message: "VIP Customer returned for repeat purchase", value: "R$ 4,500" },
  { type: "update", message: "Revenue target for Q3 exceeded by 12%" },
  { type: "stock", message: "Low inventory warning: Furniture category" },
];

export function LiveActivityCenter() {
  const [events, setEvents] = useState<StreamEvent[]>(() =>
    Array.from({ length: 5 }).map((_, i) => ({
      id: `evt-init-${i}`,
      type: EVENT_TEMPLATES[i % EVENT_TEMPLATES.length].type as any,
      message: EVENT_TEMPLATES[i % EVENT_TEMPLATES.length].message,
      time: new Date(Date.now() - i * 60000),
      value: EVENT_TEMPLATES[i % EVENT_TEMPLATES.length].value,
    })),
  );

  useEffect(() => {
    // Simulate incoming stream
    const interval = setInterval(() => {
      const template = EVENT_TEMPLATES[Math.floor(Math.random() * EVENT_TEMPLATES.length)];
      const newEvent: StreamEvent = {
        id: `evt-${Date.now()}`,
        type: template.type as any,
        message: template.message,
        time: new Date(),
        value: template.value,
      };

      setEvents((prev) => [newEvent, ...prev].slice(0, 50));
    }, 8000); // New event every 8 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-full bg-card/95 backdrop-blur-xl border-l border-border shadow-2xl">
      <div className="p-4 border-b border-border/50 flex items-center justify-between bg-black/20">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary animate-pulse" />
          <h2 className="font-semibold text-sm tracking-wide">Live Activity Stream</h2>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded text-[10px] font-bold uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Connected
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence initial={false}>
          {events.map((event) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="p-3 rounded-lg border border-border/50 bg-black/10 flex items-start gap-3 relative overflow-hidden group"
            >
              <div className="absolute inset-y-0 left-0 w-1 bg-primary/50 group-hover:bg-primary transition-colors" />
              
              <div className={cn(
                "p-2 rounded-full shrink-0",
                event.type === "purchase" ? "bg-emerald-500/20 text-emerald-500" :
                event.type === "alert" ? "bg-destructive/20 text-destructive" :
                event.type === "stock" ? "bg-orange-500/20 text-orange-500" :
                "bg-primary/20 text-primary"
              )}>
                {event.type === "purchase" ? <ShoppingCart className="w-4 h-4" /> :
                 event.type === "alert" ? <AlertTriangle className="w-4 h-4" /> :
                 event.type === "stock" ? <Package className="w-4 h-4" /> :
                 <ArrowUpRight className="w-4 h-4" />}
              </div>
              
              <div className="flex-1 space-y-1">
                <p className="text-xs font-medium text-foreground leading-snug">
                  {event.message}
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-muted-foreground">
                    {event.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  {event.value && (
                    <span className="text-xs font-semibold text-emerald-500">
                      {event.value}
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
