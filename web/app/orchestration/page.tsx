export const dynamic = "force-dynamic";

import { ApiError, getOrchestrationReview, type OrchestrationPlanItem } from "../../lib/api";
import { EmptyState, MetricCard, PageIntro, SectionTitle } from "../../components/sections";

type OrchestrationReviewPageProps = {
  searchParams?: Promise<{ view?: "actionable" | "all" }>;
};

function parseTimestamp(value?: string | null): number {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function sortPlansForReview(plans: OrchestrationPlanItem[]): OrchestrationPlanItem[] {
  return [...plans].sort((left, right) => {
    if (left.requires_human_review !== right.requires_human_review) {
      return left.requires_human_review ? -1 : 1;
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

function buildLowNoiseFollowUpEmphasis(plans: OrchestrationPlanItem[]): string {
  if (plans.length === 0) {
    return "No visible events to review.";
  }

  const reviewFirst = plans.filter((plan) => plan.requires_human_review);
  if (reviewFirst.length === 0) {
    return "No manual follow-up needed in this scope.";
  }

  const groupedSummaries = new Map<string, { count: number; latestAt: number }>();
  for (const plan of reviewFirst) {
    const summary = plan.strategy_summary.trim();
    const compactSummary = summary.endsWith(".") ? summary.slice(0, -1) : summary;
    if (!compactSummary) continue;
    const current = groupedSummaries.get(compactSummary) ?? { count: 0, latestAt: 0 };
    current.count += 1;
    current.latestAt = Math.max(current.latestAt, parseTimestamp(plan.queued_at ?? plan.created_at));
    groupedSummaries.set(compactSummary, current);
  }

  if (groupedSummaries.size === 0) {
    return "Manual review needed: open the queue for detailed rationale.";
  }

  const compactLines = [...groupedSummaries.entries()]
    .sort((left, right) => {
      if (left[1].count !== right[1].count) return right[1].count - left[1].count;
      if (left[1].latestAt !== right[1].latestAt) return right[1].latestAt - left[1].latestAt;
      return left[0].localeCompare(right[0]);
    })
    .slice(0, 2)
    .map(([summary, details]) => `${summary}${details.count > 1 ? ` ×${details.count}` : ""}`);

  const remaining = groupedSummaries.size - compactLines.length;
  if (remaining > 0) {
    compactLines.push(`+${remaining} more follow-up reason${remaining > 1 ? "s" : ""}.`);
  }

  return compactLines.join(" · ");
}

function buildGroupedFollowUpCue(plans: OrchestrationPlanItem[]): string {
  const reviewFirst = plans.filter((plan) => plan.requires_human_review);
  if (reviewFirst.length === 0) {
    return "No manual-review groups in this scope.";
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

export default async function OrchestrationReviewPage({ searchParams }: OrchestrationReviewPageProps) {
  const params = (await searchParams) ?? {};
  const selectedView = params.view === "all" ? "all" : "actionable";

  try {
    const review = await getOrchestrationReview();
    const summary = review.summary;
    const actionablePlans = review.plans.filter((plan) => plan.requires_human_review);
    const visiblePlans = selectedView === "all" ? review.plans : actionablePlans;
    const sortedVisiblePlans = sortPlansForReview(visiblePlans);
    const hiddenPlanCount = review.plans.length - visiblePlans.length;
    const queuedVisibleCount = sortedVisiblePlans.filter((plan) => Boolean(plan.queued_at)).length;
    const mostRecentVisibleAt = sortedVisiblePlans[0]?.queued_at ?? sortedVisiblePlans[0]?.created_at ?? null;
    const lowNoiseFollowUpEmphasis = buildLowNoiseFollowUpEmphasis(sortedVisiblePlans);
    const groupedFollowUpCue = buildGroupedFollowUpCue(sortedVisiblePlans);

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
          {!params.view ? <p className="lede compact">Weekly default: Actionable queue first to keep repeat reviews focused on items that require manual attention.</p> : null}
          {selectedView === "actionable" && hiddenPlanCount > 0 ? <p className="lede compact">Showing {visiblePlans.length} actionable items ({hiddenPlanCount} auto-continue events hidden).</p> : null}
          <p className="lede compact">
            Review snapshot: {sortedVisiblePlans.length} visible · {queuedVisibleCount} queued for delivery · Most recent event {formatTimestamp(mostRecentVisibleAt)}.
          </p>
          <p className="lede compact">Follow-up emphasis: {lowNoiseFollowUpEmphasis}</p>
          <p className="lede compact">Grouped follow-up cue: {groupedFollowUpCue}</p>
        </section>

        {visiblePlans.length === 0 ? (
          <EmptyState
            title={selectedView === "all" ? "No pending orchestration events" : "No actionable orchestration events"}
            body={selectedView === "all" ? "The runtime queue is currently clear. Return after the next notification cycle." : "No events currently require manual review. Switch to All events if you want to inspect auto-continue queue activity."}
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
                <tr><th>Event</th><th>Action</th><th>Review</th><th>Queued</th><th>Summary</th></tr>
              </thead>
              <tbody>
                {sortedVisiblePlans.map((plan) => (
                  <tr key={plan.event_id}>
                    <td>{plan.event_type}<div className="meta-label">{plan.event_id}</div></td>
                    <td>{plan.action}<div className="meta-label">{plan.bucket}</div></td>
                    <td>{plan.requires_human_review ? "Required" : "Not required"}</td>
                    <td>{formatTimestamp(plan.queued_at ?? plan.created_at)}</td>
                    <td>{plan.strategy_summary}</td>
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
