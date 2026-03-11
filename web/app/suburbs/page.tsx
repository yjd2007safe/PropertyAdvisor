const suburbs = [
  { name: "Southport", medianPrice: "$895k", medianRent: "$780/wk", trend: "Watching" },
  { name: "Burleigh Heads", medianPrice: "$1.35m", medianRent: "$950/wk", trend: "Steady" },
  { name: "Labrador", medianPrice: "$840k", medianRent: "$740/wk", trend: "Improving" }
];

export default function SuburbsPage() {
  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Suburb Dashboard</p>
        <h2>Monitor target suburbs before committing to property-level work.</h2>
        <p className="lede">
          Placeholder dashboard for median pricing, rent context, and trend state. Next pass can hydrate this from the suburb overview API.
        </p>
      </section>

      <section className="table-panel panel">
        <div className="table-header">
          <h3>Tracked suburbs</h3>
          <p>API target: <code>/api/suburbs/overview</code></p>
        </div>
        <div className="suburb-list">
          {suburbs.map((suburb) => (
            <article className="suburb-row" key={suburb.name}>
              <div>
                <h4>{suburb.name}</h4>
                <p>{suburb.trend} market posture</p>
              </div>
              <dl>
                <div><dt>Median price</dt><dd>{suburb.medianPrice}</dd></div>
                <div><dt>Median rent</dt><dd>{suburb.medianRent}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
