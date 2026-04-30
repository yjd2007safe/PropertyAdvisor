import { NextRequest, NextResponse } from "next/server";
import { postAlertScanAcknowledge } from "../../../lib/api";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const acknowledgedBy = `${formData.get("acknowledged_by") ?? ""}`.trim();
  const reason = `${formData.get("reason") ?? ""}`.trim();
  const deferredUntil = `${formData.get("deferred_until") ?? ""}`.trim();
  const expiresAt = `${formData.get("expires_at") ?? ""}`.trim();
  const redirectTo = `${formData.get("redirect_to") ?? "/watchlist"}`.trim();

  if (!acknowledgedBy || !reason) {
    return NextResponse.redirect(new URL(`${redirectTo}${redirectTo.includes("?") ? "&" : "?"}error=missing-ack-fields`, request.url), { status: 303 });
  }

  await postAlertScanAcknowledge({
    acknowledged_by: acknowledgedBy,
    reason,
    deferred_until: deferredUntil || undefined,
    expires_at: expiresAt || undefined,
  });
  return NextResponse.redirect(new URL(`${redirectTo}${redirectTo.includes("?") ? "&" : "?"}ack=scan-health`, request.url), { status: 303 });
}
