export const dynamic = "force-dynamic";

import { ApiError, formatCurrency, getComparables } from "../../lib/api";
import { EmptyState, MetricCard, PageIntro, SectionTitle, SummaryCardGrid, WorkflowLinks, WorkflowSnapshotPanel } from "../../components/sections";

type ComparablesPageProps = {
  searchParams?: Promise<{ query?: string; max_items?: string; min_price?: string; max_price?: string; max_distance_km?: string }>;
};

export default async function ComparablesPage({ searchParams }: ComparablesPageProps) {
  const params = (await searchParams) ?? {};
  const query = params.query ?? "";
  const maxItems = Number(params.max_items ?? "5") || 5;
  const minPrice = params.min_price ? Number(params.min_price) : undefined;
  const maxPrice = params.max_price ? Number(params.max_price) : undefined;
  const maxDistance = params.max_distance_km ? Number(params.max_distance_km) : undefined;

  try {
    const comparables = await getComparables({ query: query || undefined, max_items: maxItems, min_price: minPrice, max_price: maxPrice, max_distance_km: maxDistance });

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
        </section>

        <WorkflowSnapshotPanel snapshot={comparables.workflow_snapshot} />

        <section className="panel">
          <p className="meta-label">Data source</p>
          <p className="lede compact">{comparables.data_source.message}</p>
        </section>

        <SummaryCardGrid cards={comparables.summary_cards} />
        <WorkflowLinks links={comparables.workflow_links} />

        {comparables.items.length === 0 ? (
          <EmptyState title="No comparables found" body={comparables.narrative.action_prompt} />
        ) : (
          <>
            <section className="stats-grid">
              <MetricCard label="Comparables" value={comparables.summary.count} />
              <MetricCard label="Average price" value={formatCurrency(comparables.summary.average_price)} tone="highlight" />
              <MetricCard label="Price range" value={`${formatCurrency(comparables.summary.min_price)} - ${formatCurrency(comparables.summary.max_price)}`} />
            </section>

            <section className="panel">
              <SectionTitle eyebrow="Investor prompt" title={comparables.narrative.action_prompt} supportingText={`Then continue in advisor: /advisor?query=${comparables.query}&query_type=auto`} />
              <table className="data-table">
                <thead>
                  <tr><th>Address</th><th>Price</th><th>Sold</th><th>Config</th><th>Distance</th><th>Why it matters</th></tr>
                </thead>
                <tbody>
                  {comparables.items.map((item) => (
                    <tr key={item.address}>
                      <td>{item.address}</td>
                      <td>{formatCurrency(item.price)}</td>
                      <td>{item.sold_date}</td>
                      <td>{item.beds} bed / {item.baths} bath</td>
                      <td>{item.distance_km} km</td>
                      <td>{item.match_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
