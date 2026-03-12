export const dynamic = "force-dynamic";

import { ApiError, getPropertyAdvisor } from "../../lib/api";
import { MetricCard, PageIntro, SectionTitle } from "../../components/sections";

type AdvisorPageProps = {
  searchParams?: Promise<{ query?: string; query_type?: "address" | "slug" | "auto"; focus_strategy?: "yield" | "owner-occupier" | "balanced" }>;
};

export default async function AdvisorPage({ searchParams }: AdvisorPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const queryType = params.query_type ?? "auto";
  const focusStrategy = params.focus_strategy ?? "";

  try {
    const advisor = await getPropertyAdvisor({ query: query || undefined, query_type: queryType, focus_strategy: params.focus_strategy });

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Property Advisor"
          title="Turn a target property into a practical buy / wait decision."
          lede={advisor.decision_summary}
          aside={<><p className="meta-label">Current recommendation</p><h3>{advisor.advice.recommendation}</h3><p>Confidence: {advisor.advice.confidence}</p><p>Input mode: {advisor.inputs.query_type}</p></>}
        />

        <section className="panel">
          <form className="query-form" method="GET">
            <label htmlFor="query">Address or suburb slug</label>
            <div>
              <input id="query" name="query" defaultValue={query} placeholder="12 Example Avenue, Southport QLD 4215" />
              <select name="query_type" defaultValue={queryType}>
                <option value="auto">Auto detect</option>
                <option value="address">Address</option>
                <option value="slug">Suburb slug</option>
              </select>
              <select name="focus_strategy" defaultValue={focusStrategy}>
                <option value="">No strategy focus</option>
                <option value="balanced">Balanced</option>
                <option value="yield">Yield</option>
                <option value="owner-occupier">Owner-occupier</option>
              </select>
              <button type="submit">Run advice query</button>
            </div>
          </form>
        </section>

        <section className="stats-grid">
          <MetricCard label="Comparable sample" value={advisor.comparable_snapshot.sample_size} />
          <MetricCard label="Price position" value={advisor.comparable_snapshot.price_position} tone="highlight" />
          <MetricCard label="Strategy focus" value={advisor.market_context.strategy_focus} />
        </section>

        <section className="card-grid two-up">
          <article className="panel">
            <SectionTitle eyebrow="Subject property" title={advisor.property.address} />
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
            <SectionTitle eyebrow="Market context" title={advisor.market_context.suburb} supportingText={advisor.comparable_snapshot.summary} />
            <ul className="detail-list">
              <li><strong>Demand:</strong> {advisor.market_context.demand_signal}</li>
              <li><strong>Supply:</strong> {advisor.market_context.supply_signal}</li>
            </ul>
          </article>
        </section>

        <section className="card-grid two-up">
          <article className="panel">
            <p className="meta-label">Strengths</p>
            <ul className="detail-list">{advisor.advice.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
          <article className="panel">
            <p className="meta-label">Risks to clear first</p>
            <ul className="detail-list">{advisor.advice.risks.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
        </section>

        <section className="panel">
          <p className="meta-label">Execution plan</p>
          <ul className="detail-list">
            {advisor.advice.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </section>
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading advisor.";
    return <main className="panel"><h2>Could not load advisor data</h2><p>{message}</p></main>;
  }
}
