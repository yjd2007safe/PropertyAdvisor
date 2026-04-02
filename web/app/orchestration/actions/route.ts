import { NextRequest, NextResponse } from "next/server";

import { postOrchestrationReviewAction } from "../../../lib/api";

type ReviewerAction = "acknowledge" | "close_follow_up";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const eventId = `${formData.get("event_id") ?? ""}`.trim();
  const action = `${formData.get("action") ?? ""}`.trim() as ReviewerAction;
  const view = `${formData.get("view") ?? "actionable"}`.trim();

  if (!eventId || (action !== "acknowledge" && action !== "close_follow_up")) {
    return NextResponse.redirect(new URL(`/orchestration?view=${view}&error=invalid-action`, request.url), { status: 303 });
  }

  await postOrchestrationReviewAction({ event_id: eventId, action });
  return NextResponse.redirect(new URL(`/orchestration?view=${view}&updated=${eventId}`, request.url), { status: 303 });
}
