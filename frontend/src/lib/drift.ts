export type DriftStatus = "drifted" | "watch" | "healthy" | "unavailable";

export interface DriftPayload {
  status?: string;
  score?: number;
  n_features?: number;
  n_watch?: number;
  n_drifted?: number;
  watch_threshold?: number;
  drift_threshold?: number;
  drifted_features?: { feature: string; z_score: number }[];
  [key: string]: unknown;
}

const KNOWN: DriftStatus[] = ["drifted", "watch", "healthy"];

/** Normalize a drift payload into a stable status label. */
export function classifyDrift(drift: DriftPayload | null | undefined): DriftStatus {
  if (!drift || typeof drift.status !== "string") return "unavailable";
  return (KNOWN as string[]).includes(drift.status) ? (drift.status as DriftStatus) : "unavailable";
}

/** Tailwind border color for a drift status. */
export function driftBorderClass(status: DriftStatus): string {
  switch (status) {
    case "drifted":
      return "border-red-500/40";
    case "watch":
      return "border-amber-500/40";
    case "healthy":
      return "border-emerald-500/30";
    default:
      return "border-slate-500/30";
  }
}

/** Dot color for a drift status. */
export function driftDotColor(status: DriftStatus): string {
  switch (status) {
    case "drifted":
      return "#ef4444";
    case "watch":
      return "#f59e0b";
    case "healthy":
      return "#10b981";
    default:
      return "#94a3b8";
  }
}

/** z-score chip color for an individual feature. */
export function zScoreTone(z: number): string {
  const abs = Math.abs(z);
  if (abs >= 3) return "text-red-400";
  if (abs >= 2) return "text-amber-400";
  return "text-emerald-400";
}
