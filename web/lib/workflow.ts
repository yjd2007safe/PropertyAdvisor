export type FlowSurface = "suburbs" | "advisor" | "comparables" | "watchlist" | "alerts";

export type ComparableSort = "match" | "price_desc" | "price_asc" | "distance_asc" | "recent_sale";

type ComparableLike = {
  price: number;
  distance_km: number;
  sold_date: string;
  score?: number | null;
};

export function sanitizeQuery(value?: string | null): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

export function inferQueryType(query?: string | null): "slug" | "address" | "auto" {
  const normalized = sanitizeQuery(query);
  if (!normalized) {
    return "auto";
  }
  return normalized.includes("-") && !normalized.includes(",") ? "slug" : "address";
}

export function withFlowContext(href: string, from: FlowSurface, intent: string): string {
  const params = new URLSearchParams();
  params.set("from", from);
  params.set("intent", intent);
  return `${href}${href.includes("?") ? "&" : "?"}${params.toString()}`;
}

export function flowContextLabel(from?: string, intent?: string): string | null {
  if (!from) {
    return null;
  }
  return `Continuing from ${from}${intent ? ` (${intent})` : ""}.`;
}

export function workflowNextStepCopy(actions: string[]): string {
  const compact = actions.filter((item) => item.trim().length > 0);
  const deduped = compact.filter((item, index) => compact.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) === index);
  return deduped.length > 0 ? `Follow-up: ${deduped.join(" → ")}.` : "";
}

export function isWeeklyReviewIntent(intent?: string | null): boolean {
  const value = intent?.trim().toLowerCase();
  if (!value) {
    return false;
  }
  return value.includes("weekly") || value.includes("review") || value.includes("triage");
}

export function defaultComparablesSort(sortBy: ComparableSort | undefined, intent?: string | null): ComparableSort {
  if (sortBy) {
    return sortBy;
  }
  return isWeeklyReviewIntent(intent) ? "recent_sale" : "match";
}

export function sortComparables<T extends ComparableLike>(items: T[], sortBy: ComparableSort): T[] {
  const ranked = [...items];
  if (sortBy === "price_desc") {
    return ranked.sort((a, b) => b.price - a.price);
  }
  if (sortBy === "price_asc") {
    return ranked.sort((a, b) => a.price - b.price);
  }
  if (sortBy === "distance_asc") {
    return ranked.sort((a, b) => a.distance_km - b.distance_km);
  }
  if (sortBy === "recent_sale") {
    return ranked.sort((a, b) => Date.parse(b.sold_date) - Date.parse(a.sold_date));
  }
  return ranked.sort((a, b) => (b.score ?? Number.NEGATIVE_INFINITY) - (a.score ?? Number.NEGATIVE_INFINITY));
}

export function withUpdatedSearch(pathname: string, current: URLSearchParams, updates: Record<string, string | null | undefined>): string {
  const next = new URLSearchParams(current.toString());
  for (const [key, value] of Object.entries(updates)) {
    if (value === null || value === undefined || value.length === 0) {
      next.delete(key);
      continue;
    }
    next.set(key, value);
  }
  const query = next.toString();
  return query.length > 0 ? `${pathname}?${query}` : pathname;
}
