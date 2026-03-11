export const dynamic = "force-dynamic";

import { getPropertyAdvisor } from "../../lib/api";

type AdvisorPageProps = {
  searchParams?: Promise<{ query?: string }>;
};

export default async function AdvisorPage({ searchParams }: AdvisorPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const advisor = await getPropertyAdvisor(query || undefined);

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
          <p>Input mode: {advisor.inputs.query_type}</p>
        </div>
      </section>

      <section className="panel">
        <form className="query-form" method="GET">
          <label htmlFor="query">Address or suburb slug</label>
          <div>
            <input id="query" name="query" defaultValue={query} placeholder="12 Example Avenue, Southport QLD 4215" />
            <button type="submit">Run advice query</button>
          </div>
        </form>
      </section>

      <section className="card-grid two-up">
        <article className="panel">
          <p className="meta-label">Subject property</p>
          <h3>{advisor.property.address}</h3>
          <table className="data-table">
            <tbody>
              <tr><th>Type</th><td>{advisor.property.property_type}</td></tr>
              <tr><th>Beds</th><td>{advisor.property.beds}</td></tr>
              <tr><th>Baths</th><td>{advisor.property.baths}</td></tr>
              <tr><th>Suburb slug</th><td>{advisor.inputs.suburb_slug ?? "n/a"}</td></tr>
            </tbody>
          </table>
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
