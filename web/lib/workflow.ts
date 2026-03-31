export type FlowSurface = "suburbs" | "advisor" | "comparables" | "watchlist" | "alerts";

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
