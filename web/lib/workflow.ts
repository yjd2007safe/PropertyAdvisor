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
