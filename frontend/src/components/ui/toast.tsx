"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

type Toast = { id: number; message: string; type?: "info" | "success" | "error" };

const ToastContext = createContext<{ push: (msg: string, type?: Toast["type"]) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = (message: string, type: Toast["type"] = "info") => {
    const id = Date.now();
    const t: Toast = { id, message, type };
    setToasts((s) => [...s, t]);
    setTimeout(() => setToasts((s) => s.filter((x) => x.id !== id)), 3500);
    return id;
  };

  const dismiss = (id: number) => setToasts((s) => s.filter((x) => x.id !== id));

  // Provide a global hook for simple integrations where React context isn't easily reachable
  useEffect(() => {
    (window as any).__analytica_toast = { push, dismiss };
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      {/* Accessible live region for toasts. screen-readers will announce notifications here */}
      <div aria-live="polite" aria-atomic="true" className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => {
          const bgClass = t.type === "error" ? "bg-red-600 text-white" : t.type === "success" ? "bg-emerald-600 text-white" : "bg-card text-foreground";
          const role = t.type === "error" ? "alert" : "status";
          return (
            <div
              key={t.id}
              role={role}
              tabIndex={0}
              aria-live="polite"
              className={`px-4 py-2 rounded shadow-md text-sm flex items-start gap-3 ${bgClass}`}
            >
              <div className="flex-1">
                <div>{t.message}</div>
              </div>
              <button
                aria-label={`Dismiss notification`}
                onClick={() => dismiss(t.id)}
                className="ml-2 opacity-80 hover:opacity-100 focus:outline-none focus-visible:ring focus-visible:ring-offset-2 rounded px-2"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
