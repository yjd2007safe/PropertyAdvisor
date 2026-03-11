const workflowCards = [
  {
    title: "Suburb Dashboard",
    description: "Track suburb-level pricing, rent, yield cues, and dashboard freshness before deeper analysis.",
    href: "/suburbs"
  },
  {
    title: "Property Advisor",
    description: "Review a specific property with placeholder recommendation framing and clean integration points for real logic.",
    href: "/advisor"
  },
  {
    title: "Comparables",
    description: "Inspect the first comparable-set view and prepare the workflow for scoring, rationale, and evidence traceability.",
    href: "/comparables"
  }
];

const checklist = [
  "FastAPI skeleton ready for real services",
  "Postgres schema bootstrap flow documented locally",
  "Next.js information architecture aligned to MVP use cases"
];

export default function HomePage() {
  return (
    <main>
      <section className="hero panel">
        <p className="eyebrow">Property acquisition intelligence</p>
        <h2>One workspace for suburb signals, property advice, and comparable evidence.</h2>
        <p className="lede">
          This MVP foundation is intentionally lightweight: enough structure to run locally,
          navigate the product, and plug real market data into a coherent API and web app.
        </p>
      </section>

      <section className="stats-grid" aria-label="MVP foundation status">
        {checklist.map((item) => (
          <article className="panel stat-card" key={item}>
            <p>{item}</p>
          </article>
        ))}
      </section>

      <section className="section-block">
        <div className="section-heading">
          <p className="eyebrow">Core flows</p>
          <h3>Start with the three surfaces that matter most.</h3>
        </div>
        <div className="card-grid">
          {workflowCards.map((card) => (
            <a className="panel product-card" href={card.href} key={card.title}>
              <h4>{card.title}</h4>
              <p>{card.description}</p>
              <span>Open flow →</span>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
