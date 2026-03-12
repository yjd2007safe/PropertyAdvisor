export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getComparables } from "../../lib/api";

type ComparablesPageProps = {
  searchParams?: Promise<{ query?: string; max_items?: string }>;
};

export default async function ComparablesPage({ searchParams }: ComparablesPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const maxItems = Number(params.max_items ?? "5") || 5;

  try {
    const comparables = await getComparables({ query: query || undefined, max_items: maxItems });

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
              <input id="max_items" name="max_items" type="number" min={1} max={20} defaultValue={maxItems} />
              <button type="submit">Find comparables</button>
            </div>
          </form>
        </section>

        {comparables.items.length === 0 ? (
          <section className="panel">
            <h3>No comparables found</h3>
            <p className="lede">Try broadening your suburb/address query or increase max items.</p>
          </section>
        ) : (
          <>
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
                  <tr><th>Address</th><th>Price</th><th>Sold</th><th>Config</th><th>Distance</th><th>Match reason</th></tr>
                </thead>
                <tbody>
                  {comparables.items.map((item) => (
                    <tr key={item.address}>
                      <td>{item.address}</td>
                      <td>{formatCurrency(item.price)}</td>
                      <td>{item.sold_date}</td>
                      <td>{item.beds} bed / {item.baths} bath</td>
                      <td>{item.distance_km} km</td>
                      <td>{item.match_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading comparables.";
    return <main className="panel"><h2>Could not load comparables</h2><p>{message}</p></main>;
  }
}
