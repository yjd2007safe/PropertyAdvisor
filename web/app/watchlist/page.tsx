export const dynamic = "force-dynamic";

import { ApiError, getWatchlist } from "../../lib/api";

type WatchlistPageProps = {
  searchParams?: Promise<{ suburb_slug?: string }>;
};

export default async function WatchlistPage({ searchParams }: WatchlistPageProps) {
  const params = (await searchParams) ?? {};

  try {
    const watchlist = await getWatchlist(params.suburb_slug);

    return (
      <main className="section-stack">
        <section className="panel">
          <p className="eyebrow">Watchlist & Alerts</p>
          <h2>Track suburb signals and lightweight alerts.</h2>
          <p className="lede">Data mode: {watchlist.mode}. Filter by suburb slug for quick checks.</p>
        </section>

        <section className="panel">
          <form className="query-form" method="GET">
            <label htmlFor="suburb_slug">Filter by suburb slug</label>
            <div>
              <input id="suburb_slug" name="suburb_slug" defaultValue={params.suburb_slug ?? ""} placeholder="southport-qld-4215" />
              <button type="submit">Apply filter</button>
            </div>
          </form>
        </section>

        {watchlist.items.length === 0 ? (
          <section className="panel">
            <h3>No watchlist entries for this filter</h3>
          </section>
        ) : (
          <section className="panel">
            <table className="data-table">
              <thead>
                <tr><th>Suburb</th><th>Strategy</th><th>Notes</th><th>Alerts</th></tr>
              </thead>
              <tbody>
                {watchlist.items.map((entry) => (
                  <tr key={entry.suburb_slug}>
                    <td>{entry.suburb_name}</td>
                    <td>{entry.strategy}</td>
                    <td>{entry.notes}</td>
                    <td>
                      <ul>
                        {entry.alerts.map((alert) => (
                          <li key={`${entry.suburb_slug}-${alert.title}`}>
                            <strong>{alert.severity}</strong> · {alert.title}: {alert.detail}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    );
  } catch (error) {
    const message = error instanceof ApiError ? `${error.message}.` : "Unexpected error loading watchlist.";
    return <main className="panel"><h2>Could not load watchlist</h2><p>{message}</p></main>;
  }
}
