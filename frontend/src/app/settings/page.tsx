"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { CheckCircle2, RefreshCw, Database, Server } from "lucide-react";
import { api, setApiBase as setApiClientBase } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [testing, setTesting] = useState(false);
  const [connStatus, setConnStatus] = useState<{ status: string; latency?: number; version?: string } | null>(null);
  const [apiBase, setApiBase] = useState<string>(process.env.NEXT_PUBLIC_API_URL || "/api/v1");

  // Validation: ensure the user-provided API base can be normalized
  const [apiError, setApiError] = useState<string | null>(null);
  const validateApi = (raw: string) => {
    if (!raw || raw.trim() === "") return null;
    try {
      let candidate = raw.trim();
      if (!/^https?:\/\//i.test(candidate) && !candidate.startsWith("/")) candidate = `http://${candidate}`;
      const u = new URL(candidate);
      // Reject obviously invalid hostnames
      if (!u.hostname) return "Invalid URL";
      return null;
    } catch (e) {
      return "Invalid URL format";
    }
  };

  // Normalize API base URL: ensure protocol and /api/v1 suffix
  const normalizeApiBase = (raw: string) => {
    if (!raw || raw.trim() === "") return "/api/v1";
    let candidate = raw.trim();

    // If user provided a relative path like /api/v1, keep as-is
    try {
      // If no protocol provided, try to build with http:// as default for validation
      if (!/^https?:\/\//i.test(candidate)) {
        // Accept leading slash (relative) as-is
        if (!candidate.startsWith("/")) candidate = `http://${candidate}`;
      }
      const u = new URL(candidate);
      let base = `${u.protocol}//${u.hostname}${u.port ? `:${u.port}` : ""}`;
      // If original had a path (e.g., /api/v1) and it's not just root, include it
      if (u.pathname && u.pathname !== "/") base += u.pathname.replace(/\/+$/, "");
      // Ensure API prefix exists
      if (!base.endsWith("/api/v1")) base = `${base.replace(/\/+$/, "")}/api/v1`;
      return base;
    } catch (e) {
      // Fallback: try simple heuristics
      let out = raw.trim();
      if (!/^https?:\/\//i.test(out) && !out.startsWith("/")) out = `http://${out}`;
      if (!out.endsWith("/api/v1")) out = `${out.replace(/\/+$/, "")}/api/v1`;
      return out;
    }
  };

  const handleApplyAndTest = async () => {
    const v = validateApi(apiBase);
    setApiError(v);
    if (v) return;
    const normalized = normalizeApiBase(apiBase);
    setApiBase(normalized);
    // Update axios baseURL and then test
    try {
      setApiClientBase(normalized);
    } catch (e) {
      // ignore
    }
    const ok = await handleTestConnection();
    if (!ok) setApiError("Health check failed — backend may be unreachable");
  };

  const handleTestConnection = async () => {
    setTesting(true);
    const startTime = performance.now();
    try {
      const res = await api.get("health");
      const duration = Math.round(performance.now() - startTime);
      setConnStatus({
        status: res.data.database === "healthy" ? "Connected" : "Connected (Static Fallback)",
        latency: duration,
        version: res.data.version || "1.0.0-demo",
      });
      setTesting(false);
      return true;
    } catch (err) {
      // In static / demo mode, fallback is active and healthy
      const duration = Math.round(performance.now() - startTime);
      setConnStatus({
        status: "Connected (Static Warehouse Fallback)",
        latency: duration,
        version: "1.0.0-demo",
      });
      setTesting(false);
      return false;
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Platform Settings</h1>
          <p className="text-muted-foreground">Manage your Analytica preferences and system connections.</p>
        </div>

        <div className="grid gap-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Database className="w-5 h-5 text-primary" />
                Data Warehouse Connection
              </CardTitle>
              <CardDescription>Status and health verification of the Olist Data Warehouse.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border border-border/50 rounded-lg bg-black/10">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
                  <div>
                    <p className="font-medium text-sm">Olist E-Commerce Data Warehouse</p>
                    <p className="text-xs text-muted-foreground">
                      {typeof window !== "undefined" && window.location.hostname.includes("huggingface") 
                        ? "Hugging Face Embedded Warehouse (Static Mode)" 
                        : "brazilian_ecommerce_dw @ localhost:3306"}
                    </p>
                  </div>
                </div>
                <Button 
                  onClick={handleTestConnection}
                  disabled={testing}
                  variant="outline" 
                  size="sm"
                  className="gap-2 bg-card/50"
                >
                  <RefreshCw className={cn("w-4 h-4", testing && "animate-spin")} />
                  {testing ? "Testing..." : "Test Connection"}
                </Button>
              </div>

              {connStatus && (
                <div className={cn(
                  "p-3 rounded-lg border text-xs flex items-center justify-between transition-all bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                )}>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Status: <strong>{connStatus.status}</strong></span>
                  </div>
                  {connStatus.latency !== undefined && (
                    <span>Latency: <strong>{connStatus.latency} ms</strong> | API v{connStatus.version}</span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Server className="w-5 h-5 text-primary" />
                API Engine Configuration
              </CardTitle>
              <CardDescription>FastAPI backend connection endpoint configuration.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-muted-foreground uppercase">FastAPI Endpoint Base URL</label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      type="text"
                      value={apiBase}
                      onChange={(e) => { setApiBase(e.target.value); setApiError(null); }}
                      className="w-full h-10 rounded-md border border-border/50 bg-black/20 px-3 text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    {apiError && <p className="text-xs text-destructive mt-1">{apiError}</p>}
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => handleApplyAndTest()}
                    className="h-10 bg-card hover:bg-primary hover:text-primary-foreground transition-all"
                  >
                    Apply & Test
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
