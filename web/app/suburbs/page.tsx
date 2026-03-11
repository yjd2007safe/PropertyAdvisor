export const dynamic = "force-dynamic";

import { formatCurrency, getSuburbsOverview } from "../../lib/api";

export default async function SuburbsPage() {
  const suburbs = await getSuburbsOverview();

  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Suburb Dashboard</p>
        <h2>Monitor target suburbs before committing to property-level work.</h2>
        <p className="lede">
          Showing a practical MVP suburb snapshot from the backend service layer.
        </p>
      </section>

      <section className="table-panel panel">
        <div className="table-header">
          <h3>Tracked suburbs ({suburbs.summary.tracked_suburbs})</h3>
          <p>Freshness: {suburbs.summary.data_freshness}</p>
        </div>
        <div className="suburb-list">
          {suburbs.items.map((suburb) => (
            <article className="suburb-row" key={suburb.slug}>
              <div>
                <h4>{suburb.name}</h4>
                <p>{suburb.trend} market posture</p>
                <p>{suburb.note}</p>
              </div>
              <dl>
                <div>
                  <dt>Median price</dt>
                  <dd>{formatCurrency(suburb.median_price)}</dd>
                </div>
                <div>
                  <dt>Median rent</dt>
                  <dd>{formatCurrency(suburb.median_rent)}/wk</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
