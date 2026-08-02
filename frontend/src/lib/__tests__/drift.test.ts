import { describe, expect, it } from "vitest";
import { classifyDrift, driftBorderClass, driftDotColor, zScoreTone, type DriftPayload } from "../drift";

describe("classifyDrift", () => {
  it("maps known statuses", () => {
    expect(classifyDrift({ status: "drifted" })).toBe("drifted");
    expect(classifyDrift({ status: "watch" })).toBe("watch");
    expect(classifyDrift({ status: "healthy" })).toBe("healthy");
  });

  it("returns unavailable for missing / unknown status", () => {
    expect(classifyDrift(null)).toBe("unavailable");
    expect(classifyDrift(undefined)).toBe("unavailable");
    expect(classifyDrift({} as DriftPayload)).toBe("unavailable");
    expect(classifyDrift({ status: "bogus" })).toBe("unavailable");
  });
});

describe("driftBorderClass", () => {
  it("returns the expected tailwind classes", () => {
    expect(driftBorderClass("drifted")).toContain("border-red-500");
    expect(driftBorderClass("watch")).toContain("border-amber-500");
    expect(driftBorderClass("healthy")).toContain("border-emerald-500");
    expect(driftBorderClass("unavailable")).toContain("border-slate-500");
  });
});

describe("driftDotColor", () => {
  it("returns hex colors per status", () => {
    expect(driftDotColor("drifted")).toBe("#ef4444");
    expect(driftDotColor("watch")).toBe("#f59e0b");
    expect(driftDotColor("healthy")).toBe("#10b981");
  });
});

describe("zScoreTone", () => {
  it("colors by magnitude", () => {
    expect(zScoreTone(3.4)).toBe("text-red-400");
    expect(zScoreTone(-3.0)).toBe("text-red-400");
    expect(zScoreTone(2.2)).toBe("text-amber-400");
    expect(zScoreTone(1.1)).toBe("text-emerald-400");
    expect(zScoreTone(0)).toBe("text-emerald-400");
  });
});
