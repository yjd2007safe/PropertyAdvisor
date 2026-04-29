export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getWatchlist, getWatchlistAlerts, getWatchlistDetail, getWatchlistEvents } from "../../lib/api";
import { AlertBadge, DataSourcePanel, EmptyState, MetricCard, PageIntro, SectionTitle, SummaryCardGrid, TransparencyPanel, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";
import { flowContextLabel, withFlowContext, workflowNextStepCopy, withUpdatedSearch } from "../../lib/workflow";

type WatchlistPageProps = {
  searchParams?: Promise<{
    suburb_slug?: string;
    strategy?: "yield" | "owner-occupier" | "balanced";
    state?: string;
    watch_status?: "active" | "review" | "paused" | "archived";
    latest_outcome?: "continue_monitoring" | "revisit_later" | "close_for_now" | "escalate_for_closer_review";
    group_by?: "none" | "state" | "strategy";
    alert_severity?: "info" | "watch" | "high";
    detail_slug?: string;
    from?: string;
    intent?: string;
  }>;
};

export default async function WatchlistPage({ searchParams }: WatchlistPageProps) {
  const reviewStatusFallback = "Review status: not recorded yet.";
  const nextStepCtaFallback = "Next step: record a review status to unlock next-step guidance.";
  const reviewBatchFallback = "Review batch: pending until a review status is recorded.";
  const reviewRationaleFallback = "Why highlighted: waiting for a recorded review status.";
  const lowDataReviewFallback = "Low-data mode: treat review status and next-step guidance as provisional.";
  const reviewSectionLabel = "Review status and next step";
  const reviewActionLabel = "Save review status";
  const scanCommand = "python -m property_advisor.alert_scan --mode auto --json";
  const scopedScanCommand = (suburbSlug: string) => `python -m property_advisor.alert_scan --mode auto --suburb-slug ${suburbSlug} --json`;

  const params = (await searchParams) ?? {};
  const defaultGroupBy = params.group_by ?? "strategy";
  const hasActiveFilters = Boolean(params.suburb_slug || params.strategy || params.state || params.watch_status || params.latest_outcome || params.alert_severity || params.detail_slug || params.group_by);
  const currentSearch = new URLSearchParams(
    Object.entries(params).flatMap(([key, value]) => (value ? [[key, value]] : []))
  );

  try {
    const detailPromise = params.detail_slug
      ? getWatchlistDetail(params.detail_slug).catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      })
      : Promise.resolve(null);

    const [watchlist, alertFeed, eventFeed, detail] = await Promise.all([
      getWatchlist({
        suburb_slug: params.suburb_slug,
        strategy: params.strategy,
        state: params.state,
        watch_status: params.watch_status,
        latest_outcome: params.latest_outcome,
        group_by: defaultGroupBy
      }),
      getWatchlistAlerts(params.alert_severity),
      getWatchlistEvents(10),
      detailPromise
    ]);
    const outcomePriority: Record<string, number> = {
      escalate_for_closer_review: 5,
      revisit_later: 4,
      unrecorded: 3,
      continue_monitoring: 2,
      close_for_now: 1,
    };
    const prioritizedItems = [...watchlist.items].sort((left, right) => {
      const leftOutcome = left.latest_context?.latest_decision?.outcome ?? "unrecorded";
      const rightOutcome = right.latest_context?.latest_decision?.outcome ?? "unrecorded";
      if ((outcomePriority[leftOutcome] ?? 0) !== (outcomePriority[rightOutcome] ?? 0)) {
        return (outcomePriority[rightOutcome] ?? 0) - (outcomePriority[leftOutcome] ?? 0);
      }
      return left.suburb_slug.localeCompare(right.suburb_slug);
    });
    const handoffContext = flowContextLabel(params.from, params.intent);
    const alertEventSummary = watchlist.summary.alert_event_summary;

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Watchlist & Alerts"
          title="Triage suburbs by action, not just by raw alerts."
          lede={watchlist.summary.investor_brief}
          aside={<><p className="meta-label">Data mode</p><h3>{watchlist.mode}</h3><p>Grouped by: {watchlist.summary.grouped_view}</p></>}
        />

        <WorkflowSnapshotPanel snapshot={watchlist.workflow_snapshot} />

        <DataSourcePanel
          status={{
            ...watchlist.data_source,
            upstream_sources: { ...watchlist.data_source.upstream_sources, alert_feed: alertFeed.data_source.source }
          }}
          label="Data source"
        />
        <TransparencyPanel
          generatedAt={watchlist.generated_at}
          latestRefreshAt={eventFeed.items[0]?.occurred_at ?? detail?.item.latest_context?.updated_at ?? null}
          snapshotCount={watchlist.summary.total_entries}
          thinDataWarning={watchlist.data_source.status_label !== "live_db" ? "Watchlist is using sample/fallback data; treat status updates as provisional." : null}
          lowConfidenceWarning={watchlist.summary.action_counts.needs_review > 0 ? `${watchlist.summary.action_counts.needs_review} suburbs still need manual review.` : null}
        />

        <SummaryCardGrid cards={watchlist.summary_cards} />
        <WorkflowLinks links={watchlist.workflow_links} />

        <section className="stats-grid">
          <MetricCard label="Entries" value={watchlist.summary.total_entries} />
          <MetricCard label="Needs review" value={watchlist.summary.action_counts.needs_review ?? 0} tone="highlight" />
          <MetricCard label="High alerts" value={watchlist.summary.alert_counts.high ?? 0} tone="highlight" />
          <MetricCard label="Ready to progress" value={watchlist.summary.action_counts.ready_to_progress ?? 0} />
        </section>
        {watchlist.summary.alert_scan_ledger?.latest_run ? (
          <section className="panel">
            <p className="meta-label">Latest alert scan run</p>
            <p className="lede compact">
              {watchlist.summary.alert_scan_ledger.latest_run.status} · {watchlist.summary.alert_scan_ledger.latest_run.timestamp} · entries {watchlist.summary.alert_scan_ledger.latest_run.counts.entries_scanned} · alerts {watchlist.summary.alert_scan_ledger.latest_run.counts.alerts_scanned} · persisted {watchlist.summary.alert_scan_ledger.latest_run.counts.persisted}
            </p>
            <p className="lede compact">Regenerate command: <code>{watchlist.summary.alert_scan_ledger.latest_run.regenerate_command}</code></p>
          </section>
        ) : null}
        {alertEventSummary ? (
          <section className="panel">
            <p className="meta-label">Evidence alert lifecycle</p>
            <p className="lede compact">
              New {alertEventSummary.lifecycle.new} · Changed {alertEventSummary.lifecycle.changed} · Continuing {alertEventSummary.lifecycle.unchanged}
              {" "}· Unresolved/actionable {alertEventSummary.unresolved} · Active {alertEventSummary.active} · Total persisted {alertEventSummary.total}
            </p>
            <p className="lede compact">
              Regenerate events: <code>{scanCommand}</code>
              {params.detail_slug ? <> · scoped: <code>{scopedScanCommand(params.detail_slug)}</code></> : null}
            </p>
          </section>
        ) : null}
        {handoffContext ? <section className="panel"><p className="lede compact">{handoffContext}</p></section> : null}

        <section className="panel">
          <form className="query-form" method="GET">
            <label htmlFor="suburb_slug">Filter watchlist</label>
            <div>
              <input id="suburb_slug" name="suburb_slug" defaultValue={params.suburb_slug ?? ""} placeholder="southport-qld-4215" />
              <select name="strategy" defaultValue={params.strategy ?? ""}>
                <option value="">All strategies</option>
                <option value="balanced">Balanced</option>
                <option value="yield">Yield</option>
                <option value="owner-occupier">Owner-occupier</option>
              </select>
              <select name="watch_status" defaultValue={params.watch_status ?? ""}>
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="review">Review</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
              </select>
              <select name="group_by" defaultValue={defaultGroupBy}>
                <option value="none">Ungrouped</option>
                <option value="state">Group by state</option>
                <option value="strategy">Group by strategy</option>
              </select>
              <select name="alert_severity" defaultValue={params.alert_severity ?? ""}>
                <option value="">All alert severities</option>
                <option value="info">Info</option>
                <option value="watch">Watch</option>
                <option value="high">High</option>
              </select>
              <select name="latest_outcome" defaultValue={params.latest_outcome ?? ""}>
                <option value="">All latest outcomes</option>
                <option value="escalate_for_closer_review">Escalate for closer review</option>
                <option value="revisit_later">Revisit later</option>
                <option value="continue_monitoring">Continue monitoring</option>
                <option value="close_for_now">Close for now</option>
              </select>
              <button type="submit">Apply filters</button>
            </div>
          </form>
          <p className="meta-label">Saved review views</p>
          <div className="inline-links">
            <a href={withUpdatedSearch("/watchlist", currentSearch, { watch_status: "active", alert_severity: "watch", group_by: "strategy", latest_outcome: "continue_monitoring" })}>Active weekly queue</a> ·{" "}
            <a href={withUpdatedSearch("/watchlist", currentSearch, { watch_status: "review", alert_severity: "high", group_by: "none", latest_outcome: "escalate_for_closer_review" })}>Needs review + escalation</a> ·{" "}
            <a href={withUpdatedSearch("/watchlist", currentSearch, { suburb_slug: null, strategy: null, state: null, watch_status: null, latest_outcome: null, alert_severity: null, group_by: "strategy", detail_slug: null })}>Reset view</a>
          </div>
          {!hasActiveFilters ? <p className="lede compact">Weekly default: grouped by strategy so recurring triage queues are visible first.</p> : null}
          <p className="lede compact">
            Latest-outcome summary: {watchlist.summary.latest_outcome_distribution.length > 0
              ? watchlist.summary.latest_outcome_distribution.map((item) => `${item.label} ×${item.count}${item.is_actionable ? " (actionable)" : ""}`).join(" · ")
              : "No latest outcomes recorded yet."}
          </p>
          <p className="lede compact">
            Latest-outcome focus: {watchlist.summary.latest_outcome_focus_cue} · Escalate {watchlist.summary.latest_outcome_breakdown.escalate_for_closer_review ?? 0} · Revisit {watchlist.summary.latest_outcome_breakdown.revisit_later ?? 0} · Continue {watchlist.summary.latest_outcome_breakdown.continue_monitoring ?? 0} · Closed {watchlist.summary.latest_outcome_breakdown.close_for_now ?? 0} · No record {watchlist.summary.latest_outcome_breakdown.unrecorded ?? 0}
          </p>
          <p className="lede compact">Action-oriented scan default: {watchlist.summary.next_step_scan_cue}</p>
          <p className="lede compact">Why items are highlighted/grouped: {watchlist.summary.compact_follow_up_grouping_cue}</p>
          <p className="lede compact">Compact next-step batches: {watchlist.summary.next_step_batching_cue}</p>
          <p className="lede compact">Session packet summary: {watchlist.summary.review_session_packet_cue}</p>
          <p className="lede compact">
            Packet split — Do-now {watchlist.summary.review_session_packet_breakdown.do_now} · Batch-later {watchlist.summary.review_session_packet_breakdown.batch_later} · Recently-closed {watchlist.summary.review_session_packet_breakdown.recently_closed}.
          </p>
          <p className="lede compact">{watchlist.summary.review_session_packet_low_volume_note}</p>
        </section>

        <section className="card-grid two-up">
          <article className="panel">
            <SectionTitle eyebrow="Status split" title="Operational workload" />
            <ul className="detail-list">
              <li>Active: {watchlist.summary.by_status.active ?? 0}</li>
              <li>Review: {watchlist.summary.by_status.review ?? 0}</li>
              <li>Paused: {watchlist.summary.by_status.paused ?? 0}</li>
              <li>Archived: {watchlist.summary.by_status.archived ?? 0}</li>
            </ul>
          </article>
          <article className="panel">
            <SectionTitle eyebrow="Strategy split" title="Pipeline mix" />
            <ul className="detail-list">
              <li>Balanced: {watchlist.summary.by_strategy.balanced ?? 0}</li>
              <li>Yield: {watchlist.summary.by_strategy.yield ?? 0}</li>
              <li>Owner-occupier: {watchlist.summary.by_strategy["owner-occupier"] ?? 0}</li>
            </ul>
          </article>
        </section>

        {watchlist.groups.length > 0 ? (
          <section className="panel">
            <p className="meta-label">Grouped view: {watchlist.summary.grouped_view}</p>
            {watchlist.groups.map((group) => (
              <div className="group-block" key={group.key}>
                <h4>{group.label}</h4>
                <p className="lede compact">{group.entries.map((entry) => entry.suburb_name).join(", ")}</p>
                <p className="lede compact">Action required: {group.action_required} · High alerts: {group.high_alerts}</p>
                <p className="meta-label">{group.compact_rationale_cue}</p>
              </div>
            ))}
          </section>
        ) : null}

        {watchlist.items.length === 0 ? (
          <EmptyState
            title="No watchlist items in this review scope"
            body="Adjust one filter (or reset view) to bring back suburbs and restore do-now, batch-later, and recently-closed packet framing."
          />
        ) : (
          <section className="panel">
            <table className="data-table">
              <thead>
                <tr><th>Suburb</th><th>Status</th><th>Strategy</th><th>Target band</th><th>Latest alert</th><th>Decision triage</th><th>Actions</th><th>Detail</th></tr>
              </thead>
              <tbody>
                {prioritizedItems.map((entry) => (
                  <tr key={entry.suburb_slug}>
                    <td>{entry.suburb_name}<div className="inline-links"><a href={`/advisor?query=${entry.suburb_slug}&query_type=slug`}>Advisor</a> · <a href={`/comparables?query=${entry.suburb_slug}`}>Comparables</a></div></td>
                    <td>{entry.watch_status}</td>
                    <td>{entry.strategy}</td>
                    <td>{formatCurrency(entry.target_buy_range_min)} - {formatCurrency(entry.target_buy_range_max)}</td>
                    <td>
                      {entry.alerts[0] ? (
                        <>
                          <AlertBadge tone={entry.alerts[0].severity}>{entry.alerts[0].title}</AlertBadge>
                          <div className="meta-label">
                            {(entry.alerts[0].event_change_state ?? "untracked").replace("unchanged", "continuing")} · {entry.alerts[0].event_action_state ?? "new"} · {entry.alerts[0].event_status ?? "open"}
                          </div>
                          <div className="meta-label">
                            changed {entry.alerts[0].event_last_changed_at ?? "n/a"} · seen {entry.alerts[0].event_last_seen_at ?? "n/a"}
                          </div>
                        </>
                      ) : "No alerts"}
                    </td>
                    <td>
                      <span className="meta-label">{entry.latest_context?.latest_decision_triage_cue ?? reviewStatusFallback}</span>
                      <div className="meta-label">{entry.latest_context?.latest_decision_next_step_cue ?? nextStepCtaFallback}</div>
                      <div className="meta-label">{entry.latest_context?.latest_decision_batch_cue ?? reviewBatchFallback}</div>
                      <div className="meta-label">{entry.latest_context?.latest_decision_rationale_cue ?? reviewRationaleFallback}</div>
                      {watchlist.data_source.status_label !== "live_db" ? <div className="meta-label">{lowDataReviewFallback}</div> : null}
                    </td>
                    <td>
                      <form method="POST" action="/watchlist/actions">
                        <input type="hidden" name="suburb_slug" value={entry.suburb_slug} />
                        <input type="hidden" name="source_surface" value="watchlist" />
                        <input type="hidden" name="redirect_to" value={`/watchlist?detail_slug=${entry.suburb_slug}&suburb_slug=${entry.suburb_slug}&from=watchlist&intent=status-updated`} />
                        <select name="watch_status" defaultValue={entry.watch_status}>
                          <option value="active">Active</option>
                          <option value="review">Review</option>
                          <option value="paused">Paused</option>
                          <option value="archived">Archived</option>
                        </select>
                        <button type="submit">{reviewActionLabel}</button>
                      </form>
                    </td>
                    <td><a href={withFlowContext(`/watchlist?detail_slug=${entry.suburb_slug}&suburb_slug=${entry.suburb_slug}`, "watchlist", "open-detail")}>Open detail</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {detail ? (
          <section className="panel">
            <p className="meta-label">Detail view</p>
            <h3>{detail.item.suburb_name}</h3>
            <p className="lede">{detail.item.notes}</p>
            <p className="lede compact">
              {workflowNextStepCopy(["Run advisor", "Validate comparables"])}{" "}
              <a href={withFlowContext(`/advisor?query=${detail.item.suburb_slug}&query_type=slug`, "watchlist", "run-advisor")}>run advisor</a> then{" "}
              <a href={withFlowContext(`/comparables?query=${detail.item.suburb_slug}`, "watchlist", "validate-pricing")}>validate comparables</a>.
            </p>
            <p className="meta-label">{reviewSectionLabel}</p>
            <ul className="detail-list">
              {detail.item.alert_event_summary ? (
                <li>
                  <strong>Alert lifecycle summary:</strong> new {detail.item.alert_event_summary.lifecycle.new} · changed {detail.item.alert_event_summary.lifecycle.changed} · continuing {detail.item.alert_event_summary.lifecycle.unchanged} · unresolved/actionable {detail.item.alert_event_summary.unresolved}
                </li>
              ) : null}
              <li><strong>Advisory:</strong> {detail.item.latest_context?.advisory ?? "No advisory context recorded yet."}</li>
              <li><strong>Comparables:</strong> {detail.item.latest_context?.comparables ?? "No comparables context recorded yet."}</li>
              <li><strong>Orchestration:</strong> {detail.item.latest_context?.orchestration ?? "No orchestration context recorded yet."}</li>
              <li><strong>Recent reviewer action memory:</strong> {detail.item.latest_context?.recent_reviewer_action_summary ?? "No recent reviewer actions recorded yet."}</li>
              {detail.item.latest_context?.latest_decision ? (
                <li><strong>Latest decision:</strong> {detail.item.latest_context.latest_decision.summary} ({detail.item.latest_context.latest_decision.outcome})</li>
              ) : (
                <li><strong>Latest decision:</strong> {reviewStatusFallback}</li>
              )}
              <li><strong>Review status cue:</strong> {detail.item.latest_context?.latest_decision_triage_cue ?? reviewStatusFallback}</li>
              <li><strong>Next-step cue:</strong> {detail.item.latest_context?.latest_decision_next_step_cue ?? nextStepCtaFallback}</li>
              <li><strong>Batch cue:</strong> {detail.item.latest_context?.latest_decision_batch_cue ?? reviewBatchFallback}</li>
              <li><strong>Rationale cue:</strong> {detail.item.latest_context?.latest_decision_rationale_cue ?? reviewRationaleFallback}</li>
              {watchlist.data_source.status_label !== "live_db" ? <li><strong>Low-data note:</strong> {lowDataReviewFallback}</li> : null}
            </ul>
            <form className="query-form" method="POST" action="/watchlist/actions">
              <label htmlFor="detail_watch_status">{reviewActionLabel}</label>
              <div>
                <input type="hidden" name="suburb_slug" value={detail.item.suburb_slug} />
                <input type="hidden" name="source_surface" value="watchlist" />
                <input type="hidden" name="redirect_to" value={`/watchlist?detail_slug=${detail.item.suburb_slug}&suburb_slug=${detail.item.suburb_slug}&from=watchlist&intent=detail-updated`} />
                <select id="detail_watch_status" name="watch_status" defaultValue={detail.item.watch_status}>
                  <option value="active">Active</option>
                  <option value="review">Review</option>
                  <option value="paused">Paused</option>
                  <option value="archived">Archived</option>
                </select>
                <select name="strategy" defaultValue={detail.item.strategy}>
                  <option value="balanced">Balanced</option>
                  <option value="yield">Yield</option>
                  <option value="owner-occupier">Owner-occupier</option>
                </select>
                <input name="notes" defaultValue={detail.item.notes} />
                <button type="submit">{reviewActionLabel}</button>
              </div>
            </form>
            <ul className="detail-list">
              {detail.item.alerts.map((alert) => (
                <li key={`${alert.metric}-${alert.observed_at}`}>
                  <AlertBadge tone={alert.severity}>{alert.severity}</AlertBadge> {alert.title} ({alert.observed_at}) — {alert.detail}
                  <div className="meta-label">
                    lifecycle={alert.event_change_state ?? "untracked"} · action={alert.event_action_state ?? "new"} · status={alert.event_status ?? "open"} · changed={alert.event_last_changed_at ?? "n/a"} · seen={alert.event_last_seen_at ?? "n/a"}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {params.detail_slug && !detail ? (
          <EmptyState title="Watchlist detail not found" body={`No entry exists for ${params.detail_slug}. Use the review table below to choose a suburb and save review status.`} />
        ) : null}

        {alertFeed.items.length === 0 ? (
          <EmptyState title="No alerts for selected severity" body="Try a broader severity filter to restore portfolio-level context." />
        ) : (
          <section className="panel">
            <p className="meta-label">Alert feed ({alertFeed.total})</p>
            <ul className="detail-list">
              {alertFeed.items.map((alert) => (
                <li key={`${alert.metric}-${alert.observed_at}-${alert.title}`}><AlertBadge tone={alert.severity}>{alert.severity}</AlertBadge> {alert.title}: {alert.detail}</li>
              ))}
            </ul>
          </section>
        )}

        {eventFeed.items.length === 0 ? (
          <EmptyState title="No recent watchlist events" body="As new alerts and orchestration updates arrive, this timeline will repopulate review-session packets for do-now, batch-later, and recently-closed work." />
        ) : (
          <section className="panel">
            <p className="meta-label">Recent change timeline ({eventFeed.total})</p>
            <ul className="detail-list">
              {eventFeed.items.map((event) => (
                <li key={event.event_id}>
                  <strong>[{event.category}]</strong> {event.title} ({event.occurred_at}) — {event.detail} {" "}
                  <a href={event.follow_up_href}>{event.follow_up_label}</a>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading watchlist.";
    return <main className="panel"><h2>Could not load watchlist</h2><p>{message}</p></main>;
  }
}
