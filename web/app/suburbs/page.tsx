export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getSuburbsOverview, getWatchlist } from "../../lib/api";
import { EmptyState, MetricCard, PageIntro, SummaryCardGrid, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";

export default async function SuburbsPage() {
  try {
    const [suburbs, watchlist] = await Promise.all([getSuburbsOverview(), getWatchlist({ group_by: "strategy" })]);

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Suburb Dashboard"
          title="Prioritise where to deploy research before property-level due diligence."
          lede="Track suburb momentum, liquidity, and watchlist context in one place, then jump into advisor and comparables workflows."
        />

        <WorkflowSnapshotPanel snapshot={suburbs.workflow_snapshot} />

        <section className="stats-grid">
          <MetricCard label="Tracked suburbs" value={suburbs.summary.tracked_suburbs} />
          <MetricCard label="Watchlist suburbs" value={suburbs.summary.watchlist_suburbs} />
          <MetricCard label="Data freshness" value={suburbs.summary.data_freshness} tone="highlight" />
        </section>

        <SummaryCardGrid cards={suburbs.investor_signals} />
        <WorkflowLinks links={suburbs.workflow_links} />

        <section className="panel">
          <p className="meta-label">Watchlist grouped by strategy</p>
          {watchlist.groups.map((group) => (
            <div key={group.key} className="group-block">
              <h4>{group.label}</h4>
              <p className="lede compact">{group.entries.map((entry) => entry.suburb_name).join(", ")}</p>
            </div>
          ))}
        </section>

        {suburbs.items.length === 0 ? (
          <EmptyState title="No suburb data loaded" body="Connect a data source or keep mock mode on to continue end-to-end product testing." />
        ) : (
          <section className="table-panel panel">
            <div className="table-header">
              <h3>Tracked suburbs</h3>
            </div>
            <table className="data-table">
              <thead>
                <tr><th>Suburb</th><th>Trend</th><th>Median price</th><th>Median rent</th><th>DOM</th><th>Vacancy</th><th>Next actions</th></tr>
              </thead>
              <tbody>
                {suburbs.items.map((suburb) => (
                  <tr key={suburb.slug}>
                    <td>{suburb.name}, {suburb.state}</td>
                    <td>{suburb.trend}</td>
                    <td>{formatCurrency(suburb.median_price)}</td>
                    <td>{formatCurrency(suburb.median_rent)}/wk</td>
                    <td>{suburb.avg_days_on_market} days</td>
                    <td>{suburb.vacancy_rate_pct}%</td>
                    <td>
                      <a href={`/advisor?query=${suburb.slug}&query_type=slug`}>Advisor</a> · <a href={`/comparables?query=${suburb.slug}`}>Comps</a> · <a href={`/watchlist?detail_slug=${suburb.slug}`}>Watchlist</a>
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
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading suburb dashboard.";
    return <main className="panel"><h2>Could not load suburb dashboard</h2><p>{message}</p></main>;
  }
}
