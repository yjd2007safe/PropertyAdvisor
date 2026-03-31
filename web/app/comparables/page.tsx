export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getComparables } from "../../lib/api";
import { DataSourcePanel, EmptyState, MetricCard, PageIntro, SectionTitle, SummaryCardGrid, TransparencyPanel, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";
import { flowContextLabel, inferQueryType, withFlowContext, withUpdatedSearch } from "../../lib/workflow";

type ComparablesPageProps = {
  searchParams?: Promise<{ query?: string; max_items?: string; min_price?: string; max_price?: string; max_distance_km?: string; from?: string; intent?: string }>;
};

export default async function ComparablesPage({ searchParams }: ComparablesPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const maxItems = Number(params.max_items ?? "5") || 5;
  const minPrice = params.min_price ? Number(params.min_price) : undefined;
  const maxPrice = params.max_price ? Number(params.max_price) : undefined;
  const maxDistance = params.max_distance_km ? Number(params.max_distance_km) : undefined;
  const handoffContext = flowContextLabel(params.from, params.intent);
  const currentSearch = new URLSearchParams(
    Object.entries(params).flatMap(([key, value]) => (value ? [[key, value]] : []))
  );

  try {
    const comparables = await getComparables({ query: query || undefined, max_items: maxItems, min_price: minPrice, max_price: maxPrice, max_distance_km: maxDistance });
    const qualitySignals = [
      comparables.summary.sample_state ? `Sample state: ${comparables.summary.sample_state}` : null,
      comparables.summary.quality_label ? `Set quality label: ${comparables.summary.quality_label}` : null,
      comparables.summary.quality_score !== undefined && comparables.summary.quality_score !== null ? `Quality score: ${comparables.summary.quality_score}` : null,
      comparables.summary.algorithm_version ? `Algorithm: ${comparables.summary.algorithm_version}` : null
    ].filter((item): item is string => Boolean(item));
    const hasThinEvidence = comparables.summary.sample_state === "low" || comparables.summary.sample_state === "empty" || comparables.summary.quality_label === "low";

    return (
      <main className="section-stack">
        <PageIntro
          eyebrow="Comparables"
          title="Stress-test the target using a consistent comparable evidence panel."
          lede={`${comparables.narrative.spread_commentary} ${comparables.narrative.investor_takeaway}`}
          aside={<><p className="meta-label">Set quality</p><h3>{comparables.set_quality}</h3><p>Position: {comparables.narrative.price_position}</p></>}
        />

        <section className="panel">
          <form className="query-form" method="GET">
            <label htmlFor="query">Address, suburb, or slug</label>
            <div>
              <input id="query" name="query" defaultValue={query} placeholder="southport or 12 Example Avenue" />
              <input id="max_items" name="max_items" type="number" min={1} max={20} defaultValue={maxItems} />
              <input id="min_price" name="min_price" type="number" min={0} defaultValue={minPrice ?? ""} placeholder="Min price" />
              <input id="max_price" name="max_price" type="number" min={0} defaultValue={maxPrice ?? ""} placeholder="Max price" />
              <input id="max_distance_km" name="max_distance_km" type="number" min={0} step="0.1" defaultValue={maxDistance ?? ""} placeholder="Max km" />
              <button type="submit">Find comparables</button>
            </div>
          </form>
          <p className="meta-label">Quick weekly filters</p>
          <div className="inline-links">
            <a href={withUpdatedSearch("/comparables", currentSearch, { max_items: "5", max_distance_km: "1.5", min_price: null, max_price: null })}>Nearby shortlist</a> ·{" "}
            <a href={withUpdatedSearch("/comparables", currentSearch, { max_items: "10", max_distance_km: "4", min_price: null, max_price: null })}>Broader market scan</a> ·{" "}
            <a href={withUpdatedSearch("/comparables", currentSearch, { min_price: null, max_price: null, max_distance_km: null, max_items: "5" })}>Reset filters</a>
          </div>
        </section>
        {handoffContext ? <section className="panel"><p className="lede compact">{handoffContext}</p></section> : null}

        <WorkflowSnapshotPanel snapshot={comparables.workflow_snapshot} />

        <DataSourcePanel status={comparables.data_source} />
        <TransparencyPanel
          generatedAt={comparables.generated_at}
          snapshotCount={comparables.summary.count}
          thinDataWarning={hasThinEvidence ? "Comparable sample is thin; pricing narrative is directional only." : null}
          lowConfidenceWarning={comparables.summary.sample_state === "empty" ? "No comparable evidence available for this query." : null}
        />

        <SummaryCardGrid cards={comparables.summary_cards} />
        <WorkflowLinks links={comparables.workflow_links} />

        {comparables.items.length === 0 ? (
          <EmptyState title="No comparables found" body={`${comparables.narrative.action_prompt} Try widening price/distance filters or continue in watchlist alerts.`} />
        ) : (
          <>
            <section className="stats-grid">
              <MetricCard label="Comparables" value={comparables.summary.count} />
              <MetricCard label="Average price" value={formatCurrency(comparables.summary.average_price)} tone="highlight" />
              <MetricCard label="Price range" value={`${formatCurrency(comparables.summary.min_price)} - ${formatCurrency(comparables.summary.max_price)}`} />
            </section>
            <section className="panel">
              <SectionTitle eyebrow="Evidence quality" title="Comparable set quality and freshness signals" supportingText="Use these checks before trusting the price narrative." />
              {qualitySignals.length > 0 ? <ul className="detail-list">{qualitySignals.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="lede compact">No explicit set-quality metadata returned.</p>}
              {hasThinEvidence ? <p className="lede compact"><strong>Thin evidence warning:</strong> treat this set as directional and widen filters or gather more recent comps.</p> : null}
            </section>

            <section className="panel">
              <SectionTitle eyebrow="Investor prompt" title={comparables.narrative.action_prompt} supportingText={`Then continue in advisor with the same target context.`} />
              <table className="data-table">
                <thead>
                  <tr><th>Rank</th><th>Address</th><th>Price</th><th>Sold</th><th>Config</th><th>Distance</th><th>Score</th><th>Why it matters</th><th>Evidence rationale</th></tr>
                </thead>
                <tbody>
                  {comparables.items.map((item, index) => (
                    <tr key={item.address}>
                      <td>{index + 1}</td>
                      <td>{item.address}</td>
                      <td>{formatCurrency(item.price)}</td>
                      <td>{item.sold_date}</td>
                      <td>{item.beds} bed / {item.baths} bath</td>
                      <td>{item.distance_km} km</td>
                      <td>{item.score ?? "n/a"}</td>
                      <td>{item.match_reason}</td>
                      <td>{item.rationale && Object.keys(item.rationale).length > 0 ? Object.entries(item.rationale).map(([key, value]) => `${key}: ${value}`).join(" · ") : "n/a"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="panel">
              <form className="query-form" method="POST" action="/watchlist/actions">
                <label htmlFor="comparables_watch_status">Move target into watchlist</label>
                <div>
                  <input type="hidden" name="suburb_slug" value={comparables.query} />
                  <input type="hidden" name="source_surface" value="comparables" />
                  <input type="hidden" name="redirect_to" value={`/watchlist?detail_slug=${comparables.query}&suburb_slug=${comparables.query}&from=comparables&intent=saved`} />
                  <select id="comparables_watch_status" name="watch_status" defaultValue="review">
                    <option value="review">Review</option>
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                    <option value="archived">Archived</option>
                  </select>
                  <button type="submit">Save to watchlist</button>
                </div>
              </form>
              <p className="lede compact">
                Next actions:{" "}
                <a href={withFlowContext(`/advisor?query=${comparables.query}&query_type=${inferQueryType(comparables.query)}`, "comparables", "apply-evidence")}>apply in advisor</a>{" "}
                then{" "}
                <a href={withFlowContext(`/watchlist?detail_slug=${comparables.query}&suburb_slug=${comparables.query}`, "comparables", "confirm-watchlist")}>confirm watchlist/alerts</a>.
              </p>
            </section>
          </>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading comparables.";
    return <main className="panel"><h2>Could not load comparables</h2><p>{message}</p></main>;
  }
}
