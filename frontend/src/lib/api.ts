import axios, { AxiosInstance } from "axios";

// dynamic import for fallback data to avoid bundling large mock datasets into main bundle
let cachedFallback: any = null;
async function loadFallbackMap() {
  if (cachedFallback) return cachedFallback;
  try {
    const mod = await import("./mockData");
    cachedFallback = mod.fallbackDataMap;
    return cachedFallback;
  } catch (e) {
    return {};
  }
}

// Detect if app is running without a live backend (static / HF Space deployment)
export const isStaticDeployment =
  typeof window !== "undefined" &&
  (window.location.hostname.includes("huggingface") ||
    window.location.hostname.includes("hf.space"));

function createApiClient(base?: string): AxiosInstance {
  const baseURL = base || process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" && !isStaticDeployment ? "http://localhost:8000/api/v1" : "/api/v1");
  const instance = axios.create({
    baseURL,
    headers: {
      "Content-Type": "application/json",
      ...(process.env.NEXT_PUBLIC_ADMIN_TOKEN
        ? {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_ADMIN_TOKEN}`,
            "X-Admin-Token": process.env.NEXT_PUBLIC_ADMIN_TOKEN,
          }
        : {}),
    },
    timeout: 5000,
  });
  return instance;
}

// module-level api instance and setter
export let api: AxiosInstance = createApiClient();
export function setApiBase(base?: string) {
  api = createApiClient(base);
}

// Generic response types
export interface APIResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
  message: string;
}

// Segment filter maps a customer segment (new / repeat / vip) onto its spend-tier
// brackets using the tier's numeric range, so it survives tier-name formatting.
function segmentTierMatches(tier: string, segment: string): boolean {
  const nums = (tier.match(/\d+(?:\.\d+)?/g) || []).map(Number);
  if (nums.length === 0) return false;
  const lower = tier.toLowerCase().includes("under") ? 0 : nums[0];
  if (segment === "new") return lower < 100;
  if (segment === "repeat") return lower >= 100 && lower < 500;
  if (segment === "vip") return lower >= 500;
  return false;
}

// Fetcher function for TanStack Query
// Falls back to static warehouse data when in static mode or backend is unreachable
export async function fetcher<T>(url: string): Promise<T> {
  const urlObj = new URL(url, "http://dummy.local");
  const cleanPath = urlObj.pathname.replace(/^\/+api\/+v1/, "");
  const searchParams = urlObj.searchParams;

  // Helper for applying fast in-memory filters
  const applyFilters = async (rawFallback: any): Promise<T> => {
    const dataCopy = Array.isArray(rawFallback) ? [...rawFallback] : { ...rawFallback };

    const month = searchParams.get("month");
    const state = searchParams.get("state");
    const category = searchParams.get("category");
    const seller = searchParams.get("seller");
    const segment = searchParams.get("segment");

    if (month && month !== "all" && month !== "all_time") {
      // Month filter does NOT apply to monthly_trend — always show full range for context
    }

    if (state && state !== "all") {
      if (dataCopy.top_states && !cleanPath.includes("geography")) {
        const filtered = dataCopy.top_states.filter((s: any) => s.state_code?.toUpperCase() === state.toUpperCase());
        if (filtered.length > 0) dataCopy.top_states = filtered;
      }
    }

    if (category && category !== "all") {
      if (dataCopy.top_categories) {
        const filtered = dataCopy.top_categories.filter((c: any) =>
          c.product_category?.toLowerCase().includes(category.toLowerCase()) ||
          category.toLowerCase().includes(c.product_category?.toLowerCase())
        );
        if (filtered.length > 0) dataCopy.top_categories = filtered;
      }
    }

    if (seller && seller !== "all") {
      if (dataCopy.top_sellers) {
        const sellerTerm = seller.toLowerCase();
        const filtered = dataCopy.top_sellers.filter((s: any) =>
          s.seller_id?.toLowerCase() === sellerTerm ||
          s.seller_city?.toLowerCase().includes(sellerTerm) ||
          s.seller_state?.toLowerCase() === sellerTerm
        );
        if (filtered.length > 0) dataCopy.top_sellers = filtered;
      }
    }

    if (segment && segment !== "all") {
      if (dataCopy.spending_tiers) {
        const filtered = dataCopy.spending_tiers.filter((t: any) => segmentTierMatches(t.tier, segment));
        if (filtered.length > 0) dataCopy.spending_tiers = filtered;
      }
    }

    // Segment filter on customer-centric endpoints (KPIs without total_orders): update
    // the customer KPI directly from the matched spend tiers.
    if (segment && segment !== "all" && dataCopy.spending_tiers && dataCopy.kpis?.total_customers && !dataCopy.kpis.total_orders) {
      const segCust = dataCopy.spending_tiers.reduce((s: number, t: any) => s + (t.customer_count || 0), 0);
      const segRev = dataCopy.spending_tiers.reduce((s: number, t: any) => s + (t.tier_revenue || 0), 0);
      if (segCust > 0) {
        dataCopy.kpis = {
          ...dataCopy.kpis,
          total_customers: { ...dataCopy.kpis.total_customers, value: segCust, formatted: segCust.toLocaleString() },
          ...(dataCopy.kpis.avg_lifetime_spend
            ? { avg_lifetime_spend: { ...dataCopy.kpis.avg_lifetime_spend, value: segRev / segCust, formatted: `R$ ${(segRev / segCust).toFixed(2)}` } }
            : {}),
        };
      }
    }

    // Recalculate top-level KPIs if filtered in fallback mode
    // Uses single-dimension ratio from the MOST SPECIFIC active filter only.
    // Avoids multiplicative scaling which produces unbounded error for correlated filters.
    if (dataCopy.kpis && (dataCopy.kpis.total_orders || dataCopy.kpis.total_items_sold || dataCopy.kpis.total_customers) && !dataCopy.kpis.total_states && (month || state || category || seller || segment)) {
      const fb = await loadFallbackMap();

      // Validate known filter values — bail out early for unknown inputs to avoid corrupting KPIs
      const knownStates = fb["/geography"]?.states || [];
      if (state && state !== "all" && !knownStates.some((s: any) => s.state_code?.toUpperCase() === state.toUpperCase())) {
        console.warn(`[API] Unknown state filter: ${state}. Skipping KPI recalculation.`);
        return dataCopy as T;
      }

      const baseRev = dataCopy.kpis?.total_revenue?.value || 15843553.26;
      const baseOrders = dataCopy.kpis?.total_orders?.value || 98666;
      const baseCust = dataCopy.kpis?.total_customers?.value || 95420;

      // Find the best single-dimension ratio. Priority order (most specific first):
      // seller > segment > state > month > category
      let revRatio: number | null = null;
      let ordRatio: number | null = null;
      let custRatio: number | null = null;

      const allMonths = fb["/sales"]?.monthly_trend || [];
      const allSellers = fb["/products"]?.top_sellers || [];
      const allCategories = fb["/products"]?.categories || fb["/sales"]?.categories || [];
      const geoStates = fb["/geography"]?.states || [];

      // Seller filter (most specific)
      if (seller && seller !== "all" && revRatio === null) {
        const sellerTerm = seller.toLowerCase();
        const item = allSellers.find((s: any) =>
          s.seller_id?.toLowerCase() === sellerTerm ||
          s.seller_city?.toLowerCase().includes(sellerTerm) ||
          s.seller_state?.toLowerCase() === sellerTerm
        );
        if (item) {
          revRatio = (item.total_revenue_generated || 0) / baseRev;
          ordRatio = (item.orders_fulfilled || 0) / baseOrders;
          custRatio = ordRatio;
        }
      }

      // Segment filter (computed from spending_tiers ratios when available, else estimate)
      if (segment && segment !== "all" && revRatio === null) {
        const tiers = dataCopy.spending_tiers?.length ? dataCopy.spending_tiers : fb["/customers"]?.spending_tiers || [];
        const totalTierCust = tiers.reduce((s: number, t: any) => s + (t.customer_count || 0), 0);
        const totalTierRev = tiers.reduce((s: number, t: any) => s + (t.tier_revenue || 0), 0);
        if (totalTierCust > 0) {
          let segCust = 0;
          let segRev = 0;
          for (const t of tiers) {
            if (segmentTierMatches(t.tier, segment)) {
              segCust += t.customer_count || 0;
              segRev += t.tier_revenue || 0;
            }
          }
          revRatio = totalTierRev > 0 ? segRev / totalTierRev : null;
          ordRatio = totalTierCust > 0 ? segCust / totalTierCust : null;
          custRatio = ordRatio;
        }
      }

      // State filter
      if (state && state !== "all" && revRatio === null) {
        const stateList = [...(dataCopy.top_states || []), ...(dataCopy.sales_by_state || []), ...(dataCopy.states || []), ...geoStates];
        const item = stateList.find((s: any) => s.state_code?.toUpperCase() === state.toUpperCase());
        if (item) {
          revRatio = (item.total_revenue || 0) / baseRev;
          ordRatio = (item.total_orders || 0) / baseOrders;
          custRatio = (item.total_customers || 0) / baseCust;
        }
      }

      // Month filter — use exec monthly_trend which has total_customers
      if (month && month !== "all" && month !== "all_time" && revRatio === null) {
        const execMonths = fb["/executive"]?.monthly_trend || [];
        const item = execMonths.find((m: any) => m.order_month === month);
        if (item) {
          revRatio = (item.total_revenue || 0) / baseRev;
          ordRatio = (item.total_orders || 0) / baseOrders;
          custRatio = item.total_customers != null ? (item.total_customers || 0) / baseCust : ordRatio;
        } else {
          // Month not found in data — set ratios to 0 so KPIs show 0 (not stale unfiltered values)
          revRatio = 0;
          ordRatio = 0;
          custRatio = 0;
        }
      }

      // Category filter
      if (category && category !== "all" && revRatio === null) {
        const item = allCategories.find((c: any) =>
          c.product_category?.toLowerCase().includes(category.toLowerCase()) ||
          category.toLowerCase().includes(c.product_category?.toLowerCase())
        );
        if (item) {
          revRatio = (item.total_revenue || 0) / baseRev;
          ordRatio = (item.total_orders || 0) / baseOrders;
          // Category data may lack total_customers — use orders ratio as approximation
          custRatio = item.total_customers != null ? (item.total_customers || 0) / baseCust : ordRatio;
        }
      }

      if (revRatio !== null && ordRatio !== null) {
        const filteredRev = baseRev * revRatio;
        const filteredOrders = Math.round(baseOrders * ordRatio);
        const filteredCust = custRatio !== null ? Math.round(baseCust * custRatio) : 0;

        // Compute AOV from filtered values
        const aov = filteredOrders > 0 ? filteredRev / filteredOrders : 0;

        const formatRev = (val: number) =>
          val >= 1e6 ? `R$ ${(val / 1e6).toFixed(2)}M` :
          val >= 1e3 ? `R$ ${(val / 1e3).toFixed(1)}k` :
          `R$ ${val.toFixed(2)}`;

        dataCopy.kpis = {
          ...dataCopy.kpis,
          ...(dataCopy.kpis.total_revenue ? { total_revenue: { ...dataCopy.kpis.total_revenue, value: filteredRev, formatted: formatRev(filteredRev) } } : {}),
          ...(dataCopy.kpis.total_orders ? { total_orders: { ...dataCopy.kpis.total_orders, value: filteredOrders, formatted: filteredOrders.toLocaleString() } } : {}),
          total_customers: { ...dataCopy.kpis.total_customers, value: filteredCust, formatted: filteredCust.toLocaleString() },
          ...(dataCopy.kpis.average_order_value ? { average_order_value: { ...dataCopy.kpis.average_order_value, value: aov, formatted: `R$ ${aov.toFixed(2)}` } } : {}),
        };
      }
    } else if (dataCopy.kpis && dataCopy.kpis.total_states && (state || month)) {
      if (state && state !== "all" && dataCopy.states) {
        const item = dataCopy.states.find((s: any) => s.state_code?.toUpperCase() === state.toUpperCase());
        if (item) {
          const rev = item.total_revenue || 0;
          const freight = item.total_freight_cost || 0;
          const formatRev = (val: number) => val >= 1e6 ? `R$ ${(val / 1e6).toFixed(2)}M` : val >= 1e3 ? `R$ ${(val / 1e3).toFixed(1)}k` : `R$ ${val.toFixed(2)}`;
          dataCopy.kpis = {
            ...dataCopy.kpis,
            total_states: { ...dataCopy.kpis.total_states, value: 1, formatted: "1" },
            total_revenue: { ...dataCopy.kpis.total_revenue, value: rev, formatted: formatRev(rev) },
            total_freight: { ...dataCopy.kpis.total_freight, value: freight, formatted: formatRev(freight) },
          };
        }
      }
    }

    return dataCopy as T;
  };

  // Instant fallback for static deployment (HF Spaces) -> 0ms latency
  if (isStaticDeployment) {
    const fb = await loadFallbackMap();
    const fallback = fb[cleanPath] || fb[cleanPath.split("?")[0]];
    if (fallback !== undefined) {
      if (typeof window !== "undefined") console.warn(`[API] Using static mock data for: ${cleanPath}`);
      return applyFilters(fallback);
    }
  }

  try {
    const response = await api.get<APIResponse<T>>(url);

    const contentType = String(response.headers?.["content-type"] ?? "");
    if (!contentType.includes("application/json")) {
      throw new Error("Non-JSON response — falling back to static data");
    }

    if (response.data && response.data.success !== undefined) {
      if (!response.data.success) {
        throw new Error(response.data.message || "An error occurred while fetching data.");
      }
      return response.data.data;
    }
    return response.data as unknown as T;
  } catch {
    const fb = await loadFallbackMap();
    const fallback = fb[cleanPath] || fb[cleanPath.split("?")[0]];
    if (fallback !== undefined) {
      return applyFilters(fallback);
    }
    throw new Error(`No data available for: ${cleanPath}`);
  }
}

