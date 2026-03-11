export const dynamic = "force-dynamic";

import { formatCurrency, getComparables } from "../../lib/api";

export default async function ComparablesPage() {
  const comparables = await getComparables();

  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Comparables</p>
        <h2>Review the evidence set behind a property recommendation.</h2>
        <p className="lede">
          Subject: {comparables.subject} · Set quality: {comparables.set_quality}
        </p>
      </section>

      <section className="card-grid">
        {comparables.items.map((item) => (
          <article className="panel comparable-card" key={item.address}>
            <p className="meta-label">Comparable</p>
            <h3>{item.address}</h3>
            <p>{formatCurrency(item.price)}</p>
            <p>{item.distance_km} km away</p>
            <p>{item.match_reason}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
