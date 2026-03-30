export const dynamic = "force-dynamic";

import { ApiError, getPropertyAdvisor } from "../../lib/api";
import { DataSourcePanel, EmptyState, MetricCard, PageIntro, SectionTitle, SummaryCardGrid, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";
import { inferQueryType, sanitizeQuery, withFlowContext } from "../../lib/workflow";

type AdvisorPageProps = {
  searchParams?: Promise<{ query?: string; query_type?: "address" | "slug" | "auto"; focus_strategy?: "yield" | "owner-occupier" | "balanced"; from?: string; intent?: string }>;
};

export default async function AdvisorPage({ searchParams }: AdvisorPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const queryType = params.query_type ?? inferQueryType(query);
  const focusStrategy = params.focus_strategy ?? "";
  const handoffContext = params.from ? `Continuing from ${params.from}${params.intent ? ` (${params.intent})` : ""}.` : null;

  try {
    const advisor = await getPropertyAdvisor({ query: query || undefined, query_type: queryType, focus_strategy: params.focus_strategy });
    const evidenceSummary = advisor.advice.evidence_summary;
    const freshness = evidenceSummary?.freshness_status ?? advisor.advice.freshness ?? "unknown";
    const evidenceStrength = evidenceSummary?.evidence_strength ?? "weak";
    const sampleDepth = evidenceSummary?.sample_depth ?? advisor.advice.sample_depth ?? "none";
    const evidenceAgreement = evidenceSummary?.evidence_agreement ?? advisor.advice.evidence_agreement ?? "unknown";
    const weakEvidenceSignals = [
      ...(advisor.advice.warnings ?? []),
      ...(advisor.advice.fallback_reasons ?? []),
      ...(advisor.advice.limitations ?? []),
      ...(evidenceSummary?.warnings ?? []),
      ...(evidenceSummary?.fallback_reasons ?? []),
      ...(evidenceSummary?.limitations ?? [])
    ];

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
        {handoffContext ? <section className="panel"><p className="lede compact">{handoffContext}</p></section> : null}

        <WorkflowSnapshotPanel snapshot={advisor.workflow_snapshot} />

        <DataSourcePanel status={advisor.data_source} />

        <SummaryCardGrid cards={advisor.summary_cards} />
        <WorkflowLinks links={advisor.workflow_links} />

        <section className="stats-grid">
          <MetricCard label="Comparable sample" value={advisor.comparable_snapshot.sample_size} />
          <MetricCard label="Price position" value={advisor.comparable_snapshot.price_position} tone="highlight" />
          <MetricCard label="Strategy focus" value={advisor.market_context.strategy_focus} />
        </section>

        <section className="panel">
          <SectionTitle eyebrow="Evidence quality" title="Decision confidence at a glance" supportingText="Freshness, strength, and agreement summarize how dependable the current recommendation is." />
          <ul className="detail-list">
            <li><strong>Freshness:</strong> {freshness}</li>
            <li><strong>Strength:</strong> {evidenceStrength}</li>
            <li><strong>Sample depth:</strong> {sampleDepth}</li>
            <li><strong>Agreement:</strong> {evidenceAgreement}</li>
            {evidenceSummary?.algorithm_version ? <li><strong>Model version:</strong> {evidenceSummary.algorithm_version}</li> : null}
          </ul>
          {evidenceSummary?.confidence_reasons && evidenceSummary.confidence_reasons.length > 0 ? (
            <>
              <p className="meta-label">Why this confidence level</p>
              <ul className="detail-list">
                {evidenceSummary.confidence_reasons.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </>
          ) : null}
          {evidenceSummary?.sections && evidenceSummary.sections.length > 0 ? (
            <>
              <p className="meta-label">Evidence sections</p>
              <ul className="detail-list">
                {evidenceSummary.sections.map((section) => (
                  <li key={section.name}>
                    <strong>{section.name}</strong> ({section.status}): {section.summary}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {weakEvidenceSignals.length > 0 ? (
            <>
              <p className="meta-label">Thin / weak evidence indicators</p>
              <ul className="detail-list">
                {[...new Set(weakEvidenceSignals)].map((item) => <li key={item}>{item}</li>)}
              </ul>
            </>
          ) : null}
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
            <p className="meta-label">Structured rationale</p>
            <ul className="detail-list">
              {advisor.rationale.map((item) => <li key={item.signal}><strong>{item.signal}</strong> ({item.stance}): {item.evidence}</li>)}
            </ul>
          </article>
          <article className="panel">
            <p className="meta-label">Investor signals</p>
            <ul className="detail-list">
              {advisor.investor_signals.map((item) => <li key={item.title}><strong>{item.title}</strong> ({item.status}): {item.detail}</li>)}
            </ul>
          </article>
        </section>

        <section className="card-grid two-up">
          <article className="panel">
            <p className="meta-label">Strengths</p>
            {advisor.advice.strengths.length === 0 ? <EmptyState title="No strengths yet" body="Add stronger inputs or comps to produce support signals." /> : <ul className="detail-list">{advisor.advice.strengths.map((item) => <li key={item}>{item}</li>)}</ul>}
          </article>
          <article className="panel">
            <p className="meta-label">Risks to clear first</p>
            {advisor.advice.risks.length === 0 ? <EmptyState title="No risks surfaced" body="Current profile has no explicit caution signals in mock mode." /> : <ul className="detail-list">{advisor.advice.risks.map((item) => <li key={item}>{item}</li>)}</ul>}
          </article>
        </section>

        <section className="panel">
          <p className="meta-label">Execution plan</p>
          <ul className="detail-list">
            {advisor.advice.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
          <p className="lede compact">
            Continue with{" "}
            <a href={withFlowContext(`/comparables?query=${sanitizeQuery(advisor.inputs.suburb_slug) ?? advisor.inputs.query}`, "advisor", "validate-pricing")}>comparables</a>{" "}
            then confirm status in{" "}
            <a href={withFlowContext(`/watchlist?detail_slug=${sanitizeQuery(advisor.inputs.suburb_slug) ?? "southport-qld-4215"}&suburb_slug=${sanitizeQuery(advisor.inputs.suburb_slug) ?? "southport-qld-4215"}`, "advisor", "triage-alerts")}>watchlist</a>.
          </p>
        </section>
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading advisor.";
    return <main className="panel"><h2>Could not load advisor data</h2><p>{message}</p></main>;
  }
}
