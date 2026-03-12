export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getWatchlist, getWatchlistAlerts, getWatchlistDetail } from "../../lib/api";
import { AlertBadge, EmptyState, MetricCard, PageIntro, SectionTitle, SummaryCardGrid, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";

type WatchlistPageProps = {
  searchParams?: Promise<{
    suburb_slug?: string;
    strategy?: "yield" | "owner-occupier" | "balanced";
    state?: string;
    watch_status?: "active" | "review" | "paused";
    group_by?: "none" | "state" | "strategy";
    alert_severity?: "info" | "watch" | "high";
    detail_slug?: string;
  }>;
};

export default async function WatchlistPage({ searchParams }: WatchlistPageProps) {
  const params = (await searchParams) ?? {};

  try {
    const [watchlist, alertFeed, detail] = await Promise.all([
      getWatchlist({
        suburb_slug: params.suburb_slug,
        strategy: params.strategy,
        state: params.state,
        watch_status: params.watch_status,
        group_by: params.group_by ?? "none"
      }),
      getWatchlistAlerts(params.alert_severity),
      params.detail_slug ? getWatchlistDetail(params.detail_slug) : Promise.resolve(null)
    ]);

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Watchlist & Alerts"
          title="Triage suburbs by action, not just by raw alerts."
          lede={watchlist.summary.investor_brief}
          aside={<><p className="meta-label">Data mode</p><h3>{watchlist.mode}</h3><p>Grouped by: {watchlist.summary.grouped_view}</p></>}
        />

        <WorkflowSnapshotPanel snapshot={watchlist.workflow_snapshot} />

        <SummaryCardGrid cards={watchlist.summary_cards} />
        <WorkflowLinks links={watchlist.workflow_links} />

        <section className="stats-grid">
          <MetricCard label="Entries" value={watchlist.summary.total_entries} />
          <MetricCard label="Needs review" value={watchlist.summary.action_counts.needs_review ?? 0} tone="highlight" />
          <MetricCard label="High alerts" value={watchlist.summary.alert_counts.high ?? 0} tone="highlight" />
          <MetricCard label="Ready to progress" value={watchlist.summary.action_counts.ready_to_progress ?? 0} />
        </section>

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
              </select>
              <select name="group_by" defaultValue={params.group_by ?? "none"}>
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
              <button type="submit">Apply filters</button>
            </div>
          </form>
        </section>

        <section className="card-grid two-up">
          <article className="panel">
            <SectionTitle eyebrow="Status split" title="Operational workload" />
            <ul className="detail-list">
              <li>Active: {watchlist.summary.by_status.active ?? 0}</li>
              <li>Review: {watchlist.summary.by_status.review ?? 0}</li>
              <li>Paused: {watchlist.summary.by_status.paused ?? 0}</li>
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
              </div>
            ))}
          </section>
        ) : null}

        {watchlist.items.length === 0 ? (
          <EmptyState title="No watchlist entries for current filters" body="Relax one filter to bring back candidate suburbs and alert context." />
        ) : (
          <section className="panel">
            <table className="data-table">
              <thead>
                <tr><th>Suburb</th><th>Status</th><th>Strategy</th><th>Target band</th><th>Latest alert</th><th>Detail</th></tr>
              </thead>
              <tbody>
                {watchlist.items.map((entry) => (
                  <tr key={entry.suburb_slug}>
                    <td>{entry.suburb_name}<div className="inline-links"><a href={`/advisor?query=${entry.suburb_slug}&query_type=slug`}>Advisor</a> · <a href={`/comparables?query=${entry.suburb_slug}`}>Comps</a></div></td>
                    <td>{entry.watch_status}</td>
                    <td>{entry.strategy}</td>
                    <td>{formatCurrency(entry.target_buy_range_min)} - {formatCurrency(entry.target_buy_range_max)}</td>
                    <td>{entry.alerts[0] ? <AlertBadge tone={entry.alerts[0].severity}>{entry.alerts[0].title}</AlertBadge> : "No alerts"}</td>
                    <td><a href={`/watchlist?detail_slug=${entry.suburb_slug}`}>Open detail</a></td>
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
              Next workflow step: <a href={`/advisor?query=${detail.item.suburb_slug}&query_type=slug`}>run advisor</a> then validate in {" "}
              <a href={`/comparables?query=${detail.item.suburb_slug}`}>comparables</a>.
            </p>
            <ul className="detail-list">
              {detail.item.alerts.map((alert) => (
                <li key={`${alert.metric}-${alert.observed_at}`}><AlertBadge tone={alert.severity}>{alert.severity}</AlertBadge> {alert.title} ({alert.observed_at}) — {alert.detail}</li>
              ))}
            </ul>
          </section>
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
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading watchlist.";
    return <main className="panel"><h2>Could not load watchlist</h2><p>{message}</p></main>;
  }
}
