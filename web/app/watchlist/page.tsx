export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getWatchlist, getWatchlistAlerts, getWatchlistDetail } from "../../lib/api";
import { MetricCard, PageIntro } from "../../components/sections";

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
          title="Run an actionable watchlist workflow across list, grouped, and detail views."
          lede={`Data mode: ${watchlist.mode}. Use grouped views and alert filters to triage what needs action this week.`}
        />

        <section className="stats-grid">
          <MetricCard label="Entries" value={watchlist.summary.total_entries} />
          <MetricCard label="Active" value={watchlist.summary.active_entries} />
          <MetricCard label="High alerts" value={watchlist.summary.alert_counts.high ?? 0} tone="highlight" />
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

        {watchlist.groups.length > 0 ? (
          <section className="panel">
            <p className="meta-label">Grouped view: {watchlist.summary.grouped_view}</p>
            {watchlist.groups.map((group) => (
              <div className="group-block" key={group.key}>
                <h4>{group.label}</h4>
                <p className="lede compact">{group.entries.map((entry) => entry.suburb_name).join(", ")}</p>
              </div>
            ))}
          </section>
        ) : null}

        <section className="panel">
          <table className="data-table">
            <thead>
              <tr><th>Suburb</th><th>Status</th><th>Strategy</th><th>Target band</th><th>Detail</th></tr>
            </thead>
            <tbody>
              {watchlist.items.map((entry) => (
                <tr key={entry.suburb_slug}>
                  <td>{entry.suburb_name}</td>
                  <td>{entry.watch_status}</td>
                  <td>{entry.strategy}</td>
                  <td>{formatCurrency(entry.target_buy_range_min)} - {formatCurrency(entry.target_buy_range_max)}</td>
                  <td><a href={`/watchlist?detail_slug=${entry.suburb_slug}`}>Open detail</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {detail ? (
          <section className="panel">
            <p className="meta-label">Detail view</p>
            <h3>{detail.item.suburb_name}</h3>
            <p className="lede">{detail.item.notes}</p>
            <ul className="detail-list">
              {detail.item.alerts.map((alert) => (
                <li key={`${alert.metric}-${alert.observed_at}`}><strong>{alert.severity}</strong> · {alert.title} ({alert.observed_at}) — {alert.detail}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="panel">
          <p className="meta-label">Alert feed ({alertFeed.total})</p>
          <ul className="detail-list">
            {alertFeed.items.map((alert) => (
              <li key={`${alert.metric}-${alert.observed_at}-${alert.title}`}><strong>{alert.severity}</strong> · {alert.title}: {alert.detail}</li>
            ))}
          </ul>
        </section>
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading watchlist.";
    return <main className="panel"><h2>Could not load watchlist</h2><p>{message}</p></main>;
  }
}
