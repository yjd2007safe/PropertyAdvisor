export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getSuburbsOverview, getWatchlist } from "../../lib/api";
import { DataSourcePanel, EmptyState, MetricCard, PageIntro, SummaryCardGrid, TransparencyPanel, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";
import { withFlowContext } from "../../lib/workflow";

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

        <DataSourcePanel status={suburbs.data_source} />
        <TransparencyPanel
          generatedAt={suburbs.generated_at}
          snapshotCount={suburbs.items.length}
          thinDataWarning={suburbs.data_source.status_label !== "live_db" ? "Dashboard is not fully DB-backed; treat suburb signals as directional." : null}
        />

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
                      <a href={withFlowContext(`/advisor?query=${suburb.slug}&query_type=slug`, "suburbs", "review-advice")}>Advisor</a> ·{" "}
                      <a href={withFlowContext(`/comparables?query=${suburb.slug}`, "suburbs", "validate-pricing")}>Comparables</a> ·{" "}
                      <a href={withFlowContext(`/watchlist?detail_slug=${suburb.slug}&suburb_slug=${suburb.slug}`, "suburbs", "triage-alerts")}>Watchlist</a>
                      <form method="POST" action="/watchlist/actions">
                        <input type="hidden" name="suburb_slug" value={suburb.slug} />
                        <input type="hidden" name="source_surface" value="suburbs" />
                        <input type="hidden" name="watch_status" value="review" />
                        <input type="hidden" name="redirect_to" value={`/watchlist?detail_slug=${suburb.slug}&suburb_slug=${suburb.slug}&from=suburbs&intent=saved`} />
                        <button type="submit">Save to watchlist</button>
                      </form>
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
