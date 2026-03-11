const pillars = [
  {
    title: "Ingest",
    description: "Collect listing, sales, rental, and suburb inputs into a single intake flow."
  },
  {
    title: "Normalize",
    description: "Convert raw source data into a consistent property-centric model."
  },
  {
    title: "Advise",
    description: "Support underwriting with comparable context, market metrics, and alert-ready outputs."
  }
];

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">PropertyAdvisor MVP</p>
        <h1>Operational scaffolding for a property intelligence web app.</h1>
        <p className="lede">
          This initial shell is ready for the next implementation pass across data intake,
          normalization, comparables, market metrics, advisory workflows, and alerting.
        </p>
      </section>

      <section className="pillars" aria-label="Core workflow pillars">
        {pillars.map((pillar) => (
          <article className="card" key={pillar.title}>
            <h2>{pillar.title}</h2>
            <p>{pillar.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
