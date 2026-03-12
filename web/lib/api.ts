const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type FetchInit = RequestInit & { next?: { revalidate?: number } };

type QueryPrimitive = string | number | boolean | undefined;

function buildSearch(params: Record<string, QueryPrimitive>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      search.append(key, String(value));
    }
  });
  const asString = search.toString();
  return asString ? `?${asString}` : "";
}

export class ApiError extends Error {
  status: number;

  constructor(path: string, status: number) {
    super(`Failed to load ${path}: ${status}`);
    this.status = status;
  }
}

async function getJson<T>(path: string, init?: FetchInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    next: init?.next ?? { revalidate: 30 }
  });

  if (!response.ok) {
    throw new ApiError(path, response.status);
  }

  return response.json() as Promise<T>;
}

export type SuburbOverviewItem = {
  slug: string;
  name: string;
  state: string;
  median_price: number;
  median_rent: number;
  trend: "watching" | "steady" | "improving";
  note: string;
  avg_days_on_market: number;
  vacancy_rate_pct: number;
};

export type SuburbsOverviewResponse = {
  generated_at: string;
  summary: {
    tracked_suburbs: number;
    watchlist_suburbs: number;
    data_freshness: string;
  };
  items: SuburbOverviewItem[];
};

export type PropertyAdvisorResponse = {
  property: {
    address: string;
    property_type: string;
    beds: number;
    baths: number;
  };
  advice: {
    recommendation: "watch" | "consider" | "pass";
    confidence: "low" | "medium" | "high";
    headline: string;
    risks: string[];
    strengths: string[];
    next_steps: string[];
  };
  market_context: {
    suburb: string;
    strategy_focus: string;
    demand_signal: string;
    supply_signal: string;
  };
  comparable_snapshot: {
    sample_size: number;
    price_position: "below_range" | "in_range" | "above_range" | "insufficient_data";
    summary: string;
  };
  decision_summary: string;
  inputs: {
    query: string;
    query_type: "address" | "slug" | "auto";
    suburb_slug?: string | null;
  };
};

export type ComparablesResponse = {
  subject: string;
  set_quality: string;
  query: string;
  summary: {
    count: number;
    min_price: number;
    max_price: number;
    average_price: number;
  };
  narrative: {
    price_position: "discount" | "aligned" | "premium" | "insufficient_data";
    spread_commentary: string;
    investor_takeaway: string;
    action_prompt: string;
  };
  items: {
    address: string;
    price: number;
    distance_km: number;
    match_reason: string;
    sold_date: string;
    beds: number;
    baths: number;
  }[];
};

export type WatchlistAlert = { severity: "info" | "watch" | "high"; title: string; detail: string; metric: string; observed_at: string };

export type WatchlistEntry = {
  suburb_slug: string;
  suburb_name: string;
  state: string;
  strategy: "yield" | "owner-occupier" | "balanced";
  watch_status: "active" | "review" | "paused";
  notes: string;
  target_buy_range_min: number;
  target_buy_range_max: number;
  alerts: WatchlistAlert[];
};

export type WatchlistResponse = {
  generated_at: string;
  mode: "mock" | "postgres";
  summary: {
    total_entries: number;
    active_entries: number;
    grouped_view: "none" | "state" | "strategy";
    alert_counts: Record<string, number>;
    by_status: Record<string, number>;
    by_strategy: Record<string, number>;
    action_counts: Record<string, number>;
    investor_brief: string;
  };
  items: WatchlistEntry[];
  groups: { key: string; label: string; entries: WatchlistEntry[]; action_required: number; high_alerts: number }[];
};

export const getSuburbsOverview = () => getJson<SuburbsOverviewResponse>("/api/suburbs/overview");

export const getPropertyAdvisor = (params?: { query?: string; query_type?: "address" | "slug" | "auto"; focus_strategy?: "yield" | "owner-occupier" | "balanced" }) =>
  getJson<PropertyAdvisorResponse>(`/api/advisor/property${buildSearch(params ?? {})}`);

export const getComparables = (params?: { query?: string; max_items?: number; min_price?: number; max_price?: number; max_distance_km?: number }) =>
  getJson<ComparablesResponse>(`/api/comparables${buildSearch(params ?? {})}`);

export const getWatchlist = (params?: {
  suburb_slug?: string;
  strategy?: "yield" | "owner-occupier" | "balanced";
  state?: string;
  watch_status?: "active" | "review" | "paused";
  group_by?: "none" | "state" | "strategy";
}) => getJson<WatchlistResponse>(`/api/watchlist${buildSearch(params ?? {})}`);

export const getWatchlistDetail = (suburb_slug: string) =>
  getJson<{ generated_at: string; mode: "mock" | "postgres"; item: WatchlistEntry }>(`/api/watchlist/${suburb_slug}`);

export const getWatchlistAlerts = (severity?: "info" | "watch" | "high") =>
  getJson<{ generated_at: string; mode: "mock" | "postgres"; total: number; items: WatchlistAlert[] }>(`/api/watchlist/alerts${buildSearch({ severity })}`);

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0
  }).format(value);
}
