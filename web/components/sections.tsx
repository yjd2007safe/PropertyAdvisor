import Link from "next/link";
import { ReactNode } from "react";
import { DataSourceStatus, SummaryCard, WorkflowLink, WorkflowSnapshot } from "../lib/api";

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

export function SummaryCardGrid({ cards }: { cards: SummaryCard[] }) {
  return (
    <section className="card-grid three-up">
      {cards.map((card) => (
        <article className="panel" key={`${card.title}-${card.value}`}>
          <p className="meta-label">{card.title}</p>
          <h4>{card.value}</h4>
          <p className="lede compact">{card.detail}</p>
        </article>
      ))}
    </section>
  );
}

export function WorkflowLinks({ links }: { links: WorkflowLink[] }) {
  return (
    <section className="panel">
      <p className="meta-label">Workflow connections</p>
      <div className="card-grid two-up">
        {links.map((link) => (
          <Link className="workflow-link" href={link.href} key={`${link.label}-${link.href}`}>
            <strong>{link.label}</strong>
            <p>{link.context}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

export function WorkflowSnapshotPanel({ snapshot }: { snapshot: WorkflowSnapshot }) {
  return (
    <section className="panel workflow-snapshot">
      <p className="meta-label">Product workflow snapshot</p>
      <h3>{snapshot.next_step}</h3>
      <p className="lede compact">{snapshot.investor_message}</p>
      <div className="workflow-row">
        <span>Stage: {snapshot.stage}</span>
        {snapshot.primary_suburb_slug ? <span>Suburb: {snapshot.primary_suburb_slug}</span> : null}
      </div>
      <Link className="workflow-cta" href={snapshot.next_href}>Continue workflow →</Link>
    </section>
  );
}


export function DataSourcePanel({ status, label = "Data source" }: { status: DataSourceStatus; label?: string }) {
  const upstream = Object.entries(status.upstream_sources);
  return (
    <section className="panel">
      <p className="meta-label">{label}</p>
      <p className="lede compact">{status.message}</p>
      <p className="lede compact">Primary: {status.source} · Consistency: {status.consistency}</p>
      {upstream.length > 0 ? <p className="lede compact">Upstreams: {upstream.map(([name, source]) => `${name}:${source}`).join(", ")}</p> : null}
    </section>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      <p className="lede">{body}</p>
    </section>
  );
}
