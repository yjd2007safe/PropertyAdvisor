"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="panel">
      <h2>Something went wrong</h2>
      <button type="button" onClick={() => reset()}>Retry</button>
    </main>
  );
}
