export const dynamic = "force-dynamic";

import { ApiError, getOrchestrationReview } from "../../lib/api";
import { EmptyState, MetricCard, PageIntro, SectionTitle } from "../../components/sections";

function formatTimestamp(value?: string | null): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-AU", { timeZone: "UTC", hour12: false }) + " UTC";
}

export default async function OrchestrationReviewPage() {
  try {
    const review = await getOrchestrationReview();
    const summary = review.summary;

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
        </section>

        {review.plans.length === 0 ? (
          <EmptyState title="No pending orchestration events" body="The runtime queue is currently clear. Return after the next notification cycle." />
        ) : (
          <section className="panel">
            <SectionTitle eyebrow="Queue" title="Prioritized orchestration events" supportingText="Top-priority plans are sorted by orchestration policy and recency." />
            <table className="data-table">
              <thead>
                <tr><th>Event</th><th>Action</th><th>Review</th><th>Queued</th><th>Summary</th></tr>
              </thead>
              <tbody>
                {review.plans.map((plan) => (
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
