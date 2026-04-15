export const dynamic = "force-dynamic";

import { ApiError, getOrchestrationReview, type OrchestrationPlanItem } from "../../lib/api";
import { EmptyState, MetricCard, PageIntro, SectionTitle } from "../../components/sections";

type OrchestrationReviewPageProps = {
  searchParams?: Promise<{
    view?: "actionable" | "all";
    outcome_focus?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review" | "unrecorded";
  }>;
};

function parseTimestamp(value?: string | null): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function sortPlansForReview(plans: OrchestrationPlanItem[]): OrchestrationPlanItem[] {
  const outcomePriority: Record<string, number> = {
    escalate_for_closer_review: 5,
    revisit_later: 4,
    unrecorded: 3,
    continue_monitoring: 2,
    close_for_now: 1,
  };
  return [...plans].sort((left, right) => {
    if (left.requires_human_review !== right.requires_human_review) {
      return left.requires_human_review ? -1 : 1;
    }
    const leftOutcome = left.reviewer_decision_outcome ?? "unrecorded";
    const rightOutcome = right.reviewer_decision_outcome ?? "unrecorded";
    if ((outcomePriority[leftOutcome] ?? 0) !== (outcomePriority[rightOutcome] ?? 0)) {
      return (outcomePriority[rightOutcome] ?? 0) - (outcomePriority[leftOutcome] ?? 0);
    }
    const rightTs = parseTimestamp(right.queued_at ?? right.created_at);
    const leftTs = parseTimestamp(left.queued_at ?? left.created_at);
    if (leftTs !== rightTs) return rightTs - leftTs;
    return left.event_id.localeCompare(right.event_id);
  });
}

function formatTimestamp(value?: string | null): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-AU", { timeZone: "UTC", hour12: false }) + " UTC";
}

function formatActionLabel(action: string): string {
  return action.replace(/[_-]+/g, " ");
}

function formatFollowUpStateLabel(state: string): string {
  const labels: Record<string, string> = {
    awaiting_outcome: "Awaiting operator outcome",
    revisit_after_recovery: "Revisit after recovery",
    waiting_on_dependency: "Waiting on dependency",
    revisit_after_resume: "Revisit after resume",
    revisit_downstream_surfaces: "Carry-forward downstream",
    monitor_delivery_ack: "Monitor delivery acknowledgement",
    monitor: "Monitor"
  };
  return labels[state] ?? state.replace(/[_-]+/g, " ");
}

function buildActiveReason(plan: OrchestrationPlanItem): string {
  const revisitReason = plan.revisit_reason.trim();
  if (!revisitReason) return "No additional revisit rationale provided.";
  return `${formatFollowUpStateLabel(plan.follow_up_state)}: ${revisitReason}`;
}

function compactSentence(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return trimmed.endsWith(".") ? trimmed.slice(0, -1) : trimmed;
}

function buildFollowUpIntentGlance(plan: OrchestrationPlanItem): string {
  const intent = formatFollowUpStateLabel(plan.follow_up_state);
  const reason = compactSentence(plan.revisit_reason) || "No additional revisit rationale provided";
  const nextNotice = compactSentence(plan.next_review_cue) || "No immediate next-review cue recorded";
  return `Focus: ${intent} · Why: ${reason} · Watch next: ${nextNotice}`;
}

function formatReviewerState(state: OrchestrationPlanItem["reviewer_action_state"]): string {
  if (state === "acknowledged") return "Acknowledged";
  if (state === "closed") return "Closed";
  return "Pending";
}

function formatReviewerAction(action?: OrchestrationPlanItem["reviewer_last_action"]): string {
  if (action === "acknowledge") return "Acknowledge";
  if (action === "close_follow_up") return "Close follow-up";
  return "No action yet";
}

function formatDecisionSupportState(state: OrchestrationPlanItem["decision_support_state"]): string {
  if (state === "mostly_stable") return "Mostly stable";
  if (state === "reopen_for_closer_review") return "Re-open for closer review";
  return "Needs active attention";
}

function formatDecisionOutcome(outcome?: OrchestrationPlanItem["reviewer_decision_outcome"] | "unrecorded" | null): string {
  if (outcome === "continue_monitoring") return "Continue monitoring";
  if (outcome === "revisit_later") return "Revisit later";
  if (outcome === "close_for_now") return "Close for now";
  if (outcome === "escalate_for_closer_review") return "Escalate for closer review";
  if (outcome === "unrecorded") return "No recorded outcome";
  return "No recorded outcome";
}

function buildFollowUpSummary(plans: OrchestrationPlanItem[]): string {
  if (plans.length === 0) {
    return "No visible orchestration items in this review scope.";
  }

  const reviewFirst = plans.filter((plan) => plan.requires_human_review && plan.reviewer_action_state !== "closed");
  if (reviewFirst.length === 0) {
    return "No manual follow-up items in this review scope.";
  }

  const compactLines = reviewFirst
    .slice(0, 2)
    .map((plan) => {
      const reason = plan.revisit_reason.trim() || plan.strategy_summary.trim() || "No reason recorded";
      const compactReason = reason.endsWith(".") ? reason.slice(0, -1) : reason;
      return `${plan.event_type}: ${formatActionLabel(plan.action)} - ${compactReason}`;
    });

  const remaining = reviewFirst.length - compactLines.length;
  if (remaining > 0) {
    compactLines.push(`+${remaining} more manual-review events`);
  }

  return compactLines.join(" · ");
}


function formatOutcomeBreakdown(breakdown: Record<string, number>): string {
  const order = [
    ["escalate_for_closer_review", "Escalate"],
    ["revisit_later", "Revisit later"],
    ["continue_monitoring", "Continue monitoring"],
    ["close_for_now", "Closed for now"],
    ["unrecorded", "No recorded outcome"],
  ] as const;
  const compact = order
    .filter(([key]) => (breakdown[key] ?? 0) > 0)
    .map(([key, label]) => `${label} ×${breakdown[key]}`);
  return compact.length > 0 ? compact.join(" · ") : "No decision outcomes recorded yet.";
}

function buildGroupedFollowUpCue(plans: OrchestrationPlanItem[]): string {
  const reviewFirst = plans.filter((plan) => plan.requires_human_review && plan.reviewer_action_state !== "closed");
  if (reviewFirst.length === 0) {
    return "No manual-review groups in this review scope.";
  }

  const grouped = new Map<string, { count: number; latestAt: number; eventTypes: string[] }>();
  for (const plan of reviewFirst) {
    const current = grouped.get(plan.action) ?? { count: 0, latestAt: 0, eventTypes: [] };
    current.count += 1;
    current.latestAt = Math.max(current.latestAt, parseTimestamp(plan.queued_at ?? plan.created_at));
    if (!current.eventTypes.includes(plan.event_type)) {
      current.eventTypes.push(plan.event_type);
    }
    grouped.set(plan.action, current);
  }

  const compactGroups = [...grouped.entries()]
    .sort((left, right) => {
      if (left[1].count !== right[1].count) return right[1].count - left[1].count;
      if (left[1].latestAt !== right[1].latestAt) return right[1].latestAt - left[1].latestAt;
      return left[0].localeCompare(right[0]);
    })
    .slice(0, 3)
    .map(([action, details]) => {
      const eventTypeLabel = details.eventTypes.slice(0, 2).join(", ");
      const overflow = details.eventTypes.length > 2 ? ` +${details.eventTypes.length - 2}` : "";
      return `${formatActionLabel(action)} ×${details.count} (${eventTypeLabel}${overflow})`;
    });

  const remainingGroups = grouped.size - compactGroups.length;
  if (remainingGroups > 0) {
    compactGroups.push(`+${remainingGroups} more group${remainingGroups > 1 ? "s" : ""}`);
  }

  return compactGroups.join(" · ");
}

function buildIntentAtGlanceRollup(plans: OrchestrationPlanItem[]): string {
  const reviewFirst = plans.filter((plan) => plan.requires_human_review && plan.reviewer_action_state !== "closed");
  if (reviewFirst.length === 0) {
    return "No manual follow-up intent cues are active in this review scope.";
  }
  const compact = reviewFirst.slice(0, 3).map((plan) => `${plan.event_type}: ${buildFollowUpIntentGlance(plan)}`);
  const remaining = reviewFirst.length - compact.length;
  if (remaining > 0) compact.push(`+${remaining} more`);
  return compact.join(" · ");
}

export default async function OrchestrationReviewPage({ searchParams }: OrchestrationReviewPageProps) {
  const params = (await searchParams) ?? {};
  const selectedView = params.view === "all" ? "all" : "actionable";

  try {
    const review = await getOrchestrationReview({ outcome_focus: params.outcome_focus });
    const summary = review.summary;
    const actionablePlans = review.plans.filter((plan) => plan.requires_human_review);
    const visiblePlans = selectedView === "all" ? review.plans : actionablePlans;
    const sortedVisiblePlans = sortPlansForReview(visiblePlans);
    const hiddenPlanCount = review.plans.length - visiblePlans.length;
    const queuedVisibleCount = sortedVisiblePlans.filter((plan) => Boolean(plan.queued_at)).length;
    const mostRecentVisibleAt = sortedVisiblePlans[0]?.queued_at ?? sortedVisiblePlans[0]?.created_at ?? null;
    const followUpSummary = buildFollowUpSummary(sortedVisiblePlans);
    const groupedFollowUpCue = buildGroupedFollowUpCue(sortedVisiblePlans);
    const intentAtGlance = buildIntentAtGlanceRollup(sortedVisiblePlans);
    const decisionSupportCounts = {
      activeAttention: sortedVisiblePlans.filter((plan) => plan.decision_support_state === "active_attention").length,
      mostlyStable: sortedVisiblePlans.filter((plan) => plan.decision_support_state === "mostly_stable").length,
      reopen: sortedVisiblePlans.filter((plan) => plan.decision_support_state === "reopen_for_closer_review").length,
    };

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Orchestration Review"
          title="Operator queue for notification/runtime orchestration"
          lede={summary.next_action}
          aside={<><p className="meta-label">Current state</p><h3>{summary.current_state}</h3><p>Freshness: {summary.freshness}</p></>}
        />

        <section className="stats-grid">
          <MetricCard label="Pending events" value={summary.pending_count} />
          <MetricCard label="Needs review" value={summary.review_required_count} tone={summary.review_needed ? "highlight" : "default"} />
          <MetricCard label="Auto-continue" value={summary.auto_continue_count} />
          <MetricCard label="Queued deliveries" value={summary.queued_count} tone={summary.queued_count > 0 ? "highlight" : "default"} />
        </section>

        <section className="panel">
          <SectionTitle eyebrow="Status" title="Current orchestration state" />
          <ul className="detail-list">
            <li>Review needed: {summary.review_needed ? "Yes" : "No"}</li>
            <li>Latest event timestamp: {formatTimestamp(summary.latest_event_at)}</li>
            <li>Snapshot generated: {formatTimestamp(summary.generated_at)}</li>
          </ul>
          <p className="meta-label">Review scope</p>
          <div className="inline-links">
            <a href="/orchestration?view=actionable">Actionable queue</a> · <a href="/orchestration?view=all">All events</a>
          </div>
          <p className="meta-label">Outcome focus</p>
          <div className="inline-links">
            <a href={`/orchestration?view=${selectedView}`}>All outcomes</a> · <a href={`/orchestration?view=${selectedView}&outcome_focus=escalate_for_closer_review`}>Escalate</a> ·{" "}
            <a href={`/orchestration?view=${selectedView}&outcome_focus=revisit_later`}>Revisit later</a> ·{" "}
            <a href={`/orchestration?view=${selectedView}&outcome_focus=continue_monitoring`}>Continue monitoring</a> ·{" "}
            <a href={`/orchestration?view=${selectedView}&outcome_focus=close_for_now`}>Close for now</a> ·{" "}
            <a href={`/orchestration?view=${selectedView}&outcome_focus=unrecorded`}>No recorded outcome</a>
          </div>
          {!params.view ? <p className="lede compact">Weekly default: Actionable queue first to keep repeat reviews focused on items that require manual attention.</p> : null}
          <p className="lede compact">
            Latest-outcome summary: {summary.latest_outcome_distribution.length > 0
              ? summary.latest_outcome_distribution.map((item) => `${item.label} ×${item.count}${item.is_actionable ? " (actionable)" : ""}`).join(" · ")
              : "No decision outcomes recorded yet."}
          </p>
          {selectedView === "actionable" && hiddenPlanCount > 0 ? <p className="lede compact">Showing {visiblePlans.length} actionable items ({hiddenPlanCount} auto-continue events hidden).</p> : null}
          {summary.active_decision_outcome_filter ? <p className="lede compact">Active outcome filter: {formatDecisionOutcome(summary.active_decision_outcome_filter)} ({summary.pending_count} of {summary.total_pending_count} items).</p> : null}
          <p className="lede compact">
            Review snapshot: {sortedVisiblePlans.length} visible · {queuedVisibleCount} queued for delivery · Most recent event {formatTimestamp(mostRecentVisibleAt)}.
          </p>
          <p className="lede compact">
            Next-step outcome framing: {sortedVisiblePlans[0]?.next_step_outcome ?? "No visible outcome memory in this review scope yet."}
          </p>
          <p className="lede compact">Follow-up summary: {followUpSummary}</p>
          <p className="lede compact">Follow-up intent at a glance: {intentAtGlance}</p>
          <p className="lede compact">Grouped follow-up cue: {groupedFollowUpCue}</p>
          <p className="lede compact">Decision-outcome triage: {summary.decision_outcome_cue}</p>
          <p className="lede compact">Action-oriented scan default: {summary.action_scan_default_cue}</p>
          <p className="lede compact">Why items are highlighted/grouped: {summary.compact_follow_up_grouping_cue}</p>
          <p className="lede compact">Compact next-step batches: {summary.next_step_batching_cue}</p>
          <p className="lede compact">Outcome groups: {formatOutcomeBreakdown(summary.decision_outcome_breakdown)}</p>
          <p className="lede compact">
            Revisit decision support: {decisionSupportCounts.activeAttention} active · {decisionSupportCounts.mostlyStable} mostly stable · {decisionSupportCounts.reopen} re-open.
          </p>
          <p className="lede compact">
            Carry-forward closure: {sortedVisiblePlans.filter((plan) => plan.is_carry_forward_follow_up && plan.reviewer_action_state === "pending").length} pending ·{" "}
            {sortedVisiblePlans.filter((plan) => plan.is_carry_forward_follow_up && plan.reviewer_action_state === "acknowledged").length} acknowledged ·{" "}
            {sortedVisiblePlans.filter((plan) => plan.is_carry_forward_follow_up && plan.reviewer_action_state === "closed").length} closed.
          </p>
        </section>

        {visiblePlans.length === 0 ? (
          <EmptyState
            title={selectedView === "all" ? "No orchestration items in this review scope" : "No actionable orchestration items in this review scope"}
            body={selectedView === "all" ? "The runtime queue is currently clear. Return after the next cycle to pick up new outcome memory and cues." : "No events currently require manual review. Switch to All events to inspect auto-continue activity and outcome memory."}
          />
        ) : (
          <section className="panel">
            <SectionTitle
              eyebrow="Queue"
              title={selectedView === "all" ? "Prioritized orchestration events" : "Prioritized actionable events"}
              supportingText={selectedView === "all" ? "Top-priority plans are sorted by orchestration policy and recency." : "Focused view for repeat weekly reviews: human-review items sorted by orchestration policy and recency."}
            />
            <table className="data-table">
              <thead>
                <tr><th>Event</th><th>Action</th><th>Review</th><th>Queued</th><th>Outcome</th><th>Next-step cue</th><th>Revisit later because</th><th>Revisit guidance</th><th>Decision memory</th><th>Reviewer state</th><th>Workflow closure</th></tr>
              </thead>
              <tbody>
                {sortedVisiblePlans.map((plan) => (
                  <tr key={plan.event_id}>
                    <td>{plan.event_type}<div className="meta-label">{plan.event_id}</div>{plan.is_carry_forward_follow_up ? <div className="meta-label">Carry-forward follow-up</div> : null}</td>
                    <td>{plan.action}<div className="meta-label">{plan.bucket} · {formatFollowUpStateLabel(plan.follow_up_state)}</div><div className="meta-label">{buildFollowUpIntentGlance(plan)}</div></td>
                    <td>{plan.requires_human_review ? "Required" : "Not required"}</td>
                    <td>{formatTimestamp(plan.queued_at ?? plan.created_at)}</td>
                    <td>{plan.next_step_outcome}</td>
                    <td>
                      Next-step cue: {plan.next_step_action_cue}
                      <div className="meta-label">Batch cue: {plan.next_step_batch_cue}</div>
                    </td>
                    <td>{buildActiveReason(plan)}</td>
                    <td>
                      {formatDecisionSupportState(plan.decision_support_state)}
                      <div className="meta-label">Triage cue: {plan.next_review_cue || "Outcome memory is low-signal here, so no triage cue is recorded yet."}</div>
                      <div className="meta-label">Guidance: {plan.revisit_guidance || "Outcome memory is low-signal here, so revisit guidance is not recorded yet."}</div>
                      <div className="meta-label">{plan.compact_rationale_cue || "Rationale cue: outcome memory is low-signal here, so highlight/grouping reason is not recorded yet."}</div>
                    </td>
                    <td>
                      {formatDecisionOutcome(plan.reviewer_decision_outcome)}
                      <div className="meta-label">{plan.reviewer_decision_summary || "Outcome memory is not recorded yet for this row."}</div>
                    </td>
                    <td>
                      {formatReviewerState(plan.reviewer_action_state)}
                      {plan.reviewer_last_action_at ? <div className="meta-label">{formatTimestamp(plan.reviewer_last_action_at)}</div> : null}
                      {plan.reviewer_last_action ? <div className="meta-label">Latest action: {formatReviewerAction(plan.reviewer_last_action)}</div> : null}
                      {plan.reviewer_last_action_rationale ? <div className="meta-label">Why: {plan.reviewer_last_action_rationale}</div> : null}
                    </td>
                    <td>
                      {plan.reviewer_available_actions.length > 0 ? (
                        <div className="inline-links">
                          {plan.reviewer_available_actions.map((action) => (
                            <form key={action} method="post" action="/orchestration/actions">
                              <input type="hidden" name="event_id" value={plan.event_id} />
                              <input type="hidden" name="view" value={selectedView} />
                              <input type="hidden" name="outcome_focus" value={params.outcome_focus ?? ""} />
                              <input type="hidden" name="action" value={action} />
                              <button type="submit">{action === "acknowledge" ? "Acknowledge" : "Close follow-up"}</button>
                            </form>
                          ))}
                        </div>
                      ) : (
                        <span className="meta-label">No actions</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading orchestration review.";
    return <main className="panel"><h2>Could not load orchestration review</h2><p>{message}</p></main>;
  }
}
