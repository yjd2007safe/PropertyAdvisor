const reasons = [
  "Recent suburb momentum looks constructive but incomplete.",
  "Comparable evidence needs DB-backed scoring before confidence can move beyond placeholder.",
  "Workflow is structured to show rationale, cautions, and next actions cleanly."
];

export default function AdvisorPage() {
  return (
    <main className="section-stack">
      <section className="panel split-hero">
        <div>
          <p className="eyebrow">Property Advisor</p>
          <h2>Frame a single-property recommendation with evidence and caution notes.</h2>
          <p className="lede">This screen is the product heart: recommendation, confidence, value framing, and what to validate next.</p>
        </div>
        <div className="panel emphasis-card">
          <p className="meta-label">Current placeholder status</p>
          <h3>Watch</h3>
          <p>Confidence: Low</p>
        </div>
      </section>

      <section className="card-grid two-up">
        <article className="panel">
          <p className="meta-label">Subject property</p>
          <h3>12 Example Avenue, Southport QLD 4215</h3>
          <ul className="detail-list">
            <li>House · 4 bed · 2 bath</li>
            <li>Initial asking guide pending</li>
            <li>API target: <code>/api/advisor/property</code></li>
          </ul>
        </article>
        <article className="panel">
          <p className="meta-label">Recommendation notes</p>
          <ul className="detail-list">
            {reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </article>
      </section>
    </main>
  );
}
