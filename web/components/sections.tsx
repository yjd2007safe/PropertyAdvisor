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

export function AlertBadge({ tone, children }: { tone: "info" | "watch" | "high"; children: ReactNode }) {
  return <span className={`alert-badge alert-${tone}`}>{children}</span>;
}

export function SectionTitle({ eyebrow, title, supportingText }: { eyebrow: string; title: string; supportingText?: string }) {
  return (
    <header>
      <p className="meta-label">{eyebrow}</p>
      <h3>{title}</h3>
      {supportingText ? <p className="lede compact">{supportingText}</p> : null}
    </header>
  );
}
