export const dynamic = "force-dynamic";

import { formatCurrency, getComparables } from "../../lib/api";

type ComparablesPageProps = {
  searchParams?: Promise<{ query?: string }>;
};

export default async function ComparablesPage({ searchParams }: ComparablesPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const comparables = await getComparables(query || undefined);

  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Comparables</p>
        <h2>Review the evidence set behind a property recommendation.</h2>
        <p className="lede">Subject: {comparables.subject} · Set quality: {comparables.set_quality}</p>
      </section>

      <section className="panel">
        <form className="query-form" method="GET">
          <label htmlFor="query">Address, suburb, or slug</label>
          <div>
            <input id="query" name="query" defaultValue={query} placeholder="southport or 12 Example Avenue" />
            <button type="submit">Find comparables</button>
          </div>
        </form>
      </section>

      <section className="card-grid">
        <article className="panel">
          <p className="meta-label">Set summary</p>
          <table className="data-table">
            <tbody>
              <tr><th>Comparables</th><td>{comparables.summary.count}</td></tr>
              <tr><th>Min price</th><td>{formatCurrency(comparables.summary.min_price)}</td></tr>
              <tr><th>Avg price</th><td>{formatCurrency(comparables.summary.average_price)}</td></tr>
              <tr><th>Max price</th><td>{formatCurrency(comparables.summary.max_price)}</td></tr>
            </tbody>
          </table>
        </article>
      </section>

      <section className="panel">
        <table className="data-table">
          <thead>
            <tr><th>Address</th><th>Price</th><th>Distance</th><th>Match reason</th></tr>
          </thead>
          <tbody>
            {comparables.items.map((item) => (
              <tr key={item.address}>
                <td>{item.address}</td>
                <td>{formatCurrency(item.price)}</td>
                <td>{item.distance_km} km</td>
                <td>{item.match_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
