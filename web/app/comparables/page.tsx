const comparables = [
  { address: "8 Nearby Street", price: "$910k", fit: "Strong location and layout match" },
  { address: "17 Sample Road", price: "$875k", fit: "Slightly lower finish but useful pricing anchor" },
  { address: "31 Harbour View", price: "$940k", fit: "More premium presentation, upper-bound check" }
];

export default function ComparablesPage() {
  return (
    <main className="section-stack">
      <section className="panel">
        <p className="eyebrow">Comparables</p>
        <h2>Review the evidence set behind a property recommendation.</h2>
        <p className="lede">
          This placeholder prepares for ranked comparable members, rationale, and set quality once scoring logic moves behind the API.
        </p>
      </section>

      <section className="card-grid">
        {comparables.map((item) => (
          <article className="panel comparable-card" key={item.address}>
            <p className="meta-label">Comparable</p>
            <h3>{item.address}</h3>
            <p>{item.price}</p>
            <p>{item.fit}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
