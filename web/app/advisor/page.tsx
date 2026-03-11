export const dynamic = "force-dynamic";

import { getPropertyAdvisor } from "../../lib/api";

export default async function AdvisorPage() {
  const advisor = await getPropertyAdvisor();

  return (
    <main className="section-stack">
      <section className="panel split-hero">
        <div>
          <p className="eyebrow">Property Advisor</p>
          <h2>Frame a single-property recommendation with evidence and caution notes.</h2>
          <p className="lede">{advisor.advice.headline}</p>
        </div>
        <div className="panel emphasis-card">
          <p className="meta-label">Current recommendation</p>
          <h3>{advisor.advice.recommendation}</h3>
          <p>Confidence: {advisor.advice.confidence}</p>
        </div>
      </section>

      <section className="card-grid two-up">
        <article className="panel">
          <p className="meta-label">Subject property</p>
          <h3>{advisor.property.address}</h3>
          <ul className="detail-list">
            <li>
              {advisor.property.property_type} · {advisor.property.beds} bed · {advisor.property.baths} bath
            </li>
            <li>Service endpoint: <code>/api/advisor/property</code></li>
          </ul>
        </article>
        <article className="panel">
          <p className="meta-label">Recommendation next steps</p>
          <ul className="detail-list">
            {advisor.advice.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
