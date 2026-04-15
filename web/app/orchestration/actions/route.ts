import { NextRequest, NextResponse } from "next/server";

import { postOrchestrationReviewAction } from "../../../lib/api";

type ReviewerAction = "acknowledge" | "close_follow_up";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const eventId = `${formData.get("event_id") ?? ""}`.trim();
  const action = `${formData.get("action") ?? ""}`.trim() as ReviewerAction;
  const view = `${formData.get("view") ?? "actionable"}`.trim();
  const outcomeFocus = `${formData.get("outcome_focus") ?? ""}`.trim();
  const reviewerActionStateFocus = `${formData.get("reviewer_action_state_focus") ?? ""}`.trim();
  const followUpStateFocus = `${formData.get("follow_up_state_focus") ?? ""}`.trim();
  const filters = `${outcomeFocus ? `&outcome_focus=${outcomeFocus}` : ""}${reviewerActionStateFocus ? `&reviewer_action_state_focus=${reviewerActionStateFocus}` : ""}${followUpStateFocus ? `&follow_up_state_focus=${followUpStateFocus}` : ""}`;

  if (!eventId || (action !== "acknowledge" && action !== "close_follow_up")) {
    return NextResponse.redirect(new URL(`/orchestration?view=${view}${filters}&error=invalid-action`, request.url), { status: 303 });
  }

  await postOrchestrationReviewAction({ event_id: eventId, action });
  return NextResponse.redirect(new URL(`/orchestration?view=${view}${filters}&updated=${eventId}`, request.url), { status: 303 });
}
