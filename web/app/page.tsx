const workflowCards = [
  {
    title: "Suburb Dashboard",
    description: "Track suburb-level pricing, rent, yield cues, and dashboard freshness before deeper analysis.",
    href: "/suburbs"
  },
  {
    title: "Property Advisor",
    description: "Review a specific property with structured rationale, investor signals, and recommendation framing.",
    href: "/advisor"
  },
  {
    title: "Comparables",
    description: "Inspect comparable evidence with summary cards and investor-facing pricing prompts.",
    href: "/comparables"
  },
  {
    title: "Watchlist",
    description: "Prioritise suburb actions by strategy, status, and alert severity in one triage queue.",
    href: "/watchlist"
  }
];

const checklist = [
  "Unified workflow links across all product surfaces",
  "Structured advisory rationale and investor signals in mock mode",
  "Service/repository seams hardened for future real-data integration"
];

export default function HomePage() {
  return (
    <main>
      <section className="hero panel">
        <p className="eyebrow">Property acquisition intelligence</p>
        <h2>One decision-support workspace from suburb scan to execution-ready shortlist.</h2>
        <p className="lede">
          This MVP stays lightweight while improving product coherence across dashboard, advisor,
          comparables, and watchlist so each step supports the next decision.
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
          <h3>Run the end-to-end investor workflow in one coherent product.</h3>
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
