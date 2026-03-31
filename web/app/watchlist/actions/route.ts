import { NextRequest, NextResponse } from "next/server";

import { postWatchlistAction } from "../../../lib/api";

type SourceSurface = "advisor" | "comparables" | "watchlist" | "suburbs";
type WatchStatus = "active" | "review" | "paused" | "archived";
type Strategy = "yield" | "owner-occupier" | "balanced";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const suburbSlug = `${formData.get("suburb_slug") ?? ""}`.trim();
  const sourceSurface = `${formData.get("source_surface") ?? "watchlist"}`.trim() as SourceSurface;
  const redirectTo = `${formData.get("redirect_to") ?? "/watchlist"}`.trim();
  const watchStatus = `${formData.get("watch_status") ?? ""}`.trim() as WatchStatus;
  const strategy = `${formData.get("strategy") ?? ""}`.trim() as Strategy;
  const notes = `${formData.get("notes") ?? ""}`.trim();

  if (!suburbSlug) {
    return NextResponse.redirect(new URL("/watchlist?error=missing-suburb", request.url), { status: 303 });
  }

  await postWatchlistAction({
    suburb_slug: suburbSlug,
    source_surface: sourceSurface,
    watch_status: watchStatus || undefined,
    strategy: strategy || undefined,
    notes: notes || undefined
  });

  return NextResponse.redirect(new URL(redirectTo, request.url), { status: 303 });
}
