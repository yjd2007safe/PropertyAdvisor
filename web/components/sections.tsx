import { ReactNode } from "react";

export function PageIntro({ eyebrow, title, lede, aside }: { eyebrow: string; title: string; lede: string; aside?: ReactNode }) {
  return (
    <section className="panel split-hero">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="lede">{lede}</p>
      </div>
      {aside ? <div className="panel emphasis-card">{aside}</div> : null}
    </section>
  );
}

export function MetricCard({ label, value, tone = "default" }: { label: string; value: ReactNode; tone?: "default" | "highlight" }) {
  return (
    <article className={`panel stat-card ${tone === "highlight" ? "stat-card-highlight" : ""}`}>
      <p className="meta-label">{label}</p>
      <strong>{value}</strong>
    </article>
  );
}
