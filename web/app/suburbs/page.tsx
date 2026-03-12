export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getSuburbsOverview, getWatchlist } from "../../lib/api";

export default async function SuburbsPage() {
  try {
    const [suburbs, watchlist] = await Promise.all([getSuburbsOverview(), getWatchlist()]);

    return (
      <main className="section-stack">
        <section className="panel">
          <p className="eyebrow">Suburb Dashboard</p>
          <h2>Monitor target suburbs before committing to property-level work.</h2>
          <p className="lede">Structured suburb snapshots plus watchlist context from the API layer.</p>
        </section>

        <section className="stats-grid">
          <article className="panel stat-card">Tracked suburbs: {suburbs.summary.tracked_suburbs}</article>
          <article className="panel stat-card">Watchlist suburbs: {suburbs.summary.watchlist_suburbs}</article>
          <article className="panel stat-card">Data freshness: {suburbs.summary.data_freshness}</article>
        </section>

        <section className="panel">
          <p className="meta-label">Watchlist pulse</p>
          {watchlist.items.length === 0 ? (
            <p className="lede">No active watchlist entries yet.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Suburb</th><th>Strategy</th><th>Latest alert</th></tr>
              </thead>
              <tbody>
                {watchlist.items.map((entry) => (
                  <tr key={entry.suburb_slug}>
                    <td>{entry.suburb_name}</td>
                    <td>{entry.strategy}</td>
                    <td>{entry.alerts[0]?.title ?? "No alerts"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="table-panel panel">
          <div className="table-header">
            <h3>Tracked suburbs</h3>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Suburb</th><th>Trend</th><th>Median price</th><th>Median rent</th><th>DOM</th><th>Vacancy</th><th>Note</th></tr>
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
                  <td>{suburb.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading suburb dashboard.";
    return <main className="panel"><h2>Could not load suburb dashboard</h2><p>{message}</p></main>;
  }
}
