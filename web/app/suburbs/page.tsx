export const dynamic = "force-dynamic";

import { formatCurrency, getSuburbsOverview } from "../../lib/api";

export default async function SuburbsPage() {
  const suburbs = await getSuburbsOverview();

  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Suburb Dashboard</p>
        <h2>Monitor target suburbs before committing to property-level work.</h2>
        <p className="lede">Showing a practical MVP suburb snapshot from the backend service layer.</p>
      </section>

      <section className="stats-grid">
        <article className="panel stat-card">Tracked suburbs: {suburbs.summary.tracked_suburbs}</article>
        <article className="panel stat-card">Watchlist suburbs: {suburbs.summary.watchlist_suburbs}</article>
        <article className="panel stat-card">Data freshness: {suburbs.summary.data_freshness}</article>
      </section>

      <section className="table-panel panel">
        <div className="table-header">
          <h3>Tracked suburbs</h3>
        </div>
        <table className="data-table">
          <thead>
            <tr><th>Suburb</th><th>Trend</th><th>Median price</th><th>Median rent</th><th>Note</th></tr>
          </thead>
          <tbody>
            {suburbs.items.map((suburb) => (
              <tr key={suburb.slug}>
                <td>{suburb.name}, {suburb.state}</td>
                <td>{suburb.trend}</td>
                <td>{formatCurrency(suburb.median_price)}</td>
                <td>{formatCurrency(suburb.median_rent)}/wk</td>
                <td>{suburb.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
