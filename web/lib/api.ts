const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type FetchInit = RequestInit & { next?: { revalidate?: number } };

async function getJson<T>(path: string, init?: FetchInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    next: init?.next ?? { revalidate: 60 }
  });

  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
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
    next_steps: string[];
  };
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
  items: {
    address: string;
    price: number;
    distance_km: number;
    match_reason: string;
  }[];
};

export const getSuburbsOverview = () => getJson<SuburbsOverviewResponse>("/api/suburbs/overview");

export const getPropertyAdvisor = (query?: string) => {
  const search = query ? `?query=${encodeURIComponent(query)}` : "";
  return getJson<PropertyAdvisorResponse>(`/api/advisor/property${search}`);
};

export const getComparables = (query?: string) => {
  const search = query ? `?query=${encodeURIComponent(query)}` : "";
  return getJson<ComparablesResponse>(`/api/comparables${search}`);
};

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0
  }).format(value);
}
