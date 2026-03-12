import Link from "next/link";
import { ReactNode } from "react";
import { SummaryCard, WorkflowLink } from "../lib/api";

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

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      <p className="lede">{body}</p>
    </section>
  );
}
