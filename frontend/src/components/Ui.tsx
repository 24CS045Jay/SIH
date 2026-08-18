import type { ReactNode } from "react";

export type Tone = "critical" | "high" | "medium" | "low" | "success" | "neutral";

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return <span className={`ui-badge ui-badge-${tone}`} role="status"><span className="ui-badge-mark" aria-hidden="true" />{label}</span>;
}

export function ConfidenceBadge({ value }: { value: number | null | undefined }) {
  const score = typeof value === "number" ? value : 0;
  const tone: Tone = score >= 0.85 ? "success" : score >= 0.7 ? "medium" : "high";
  const label = typeof value === "number" ? `${Math.round(score * 100)}% confidence` : "Confidence pending";
  return <StatusBadge label={label} tone={tone} />;
}

export function PriorityBadge({ priority }: { priority: string }) {
  const tone = priority.toLowerCase() as Tone;
  return <StatusBadge label={`${priority} priority`} tone={["critical", "high", "medium", "low"].includes(tone) ? tone : "neutral"} />;
}

export function WorkflowBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase().replaceAll(" ", "_");
  const tone: Tone = normalized.includes("completed") || normalized.includes("closed") || normalized.includes("verified") ? "success" : normalized.includes("critical") || normalized.includes("overdue") || normalized.includes("blocked") ? "high" : normalized.includes("review") || normalized.includes("progress") || normalized.includes("acknowledged") ? "medium" : "neutral";
  return <StatusBadge label={status.replaceAll("_", " ")} tone={tone} />;
}

export function SyntheticNotice({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? "synthetic-notice compact" : "synthetic-notice"} role="note"><span className="synthetic-notice-mark" aria-hidden="true">S</span><span>SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA</span></div>;
}

export function LoadingState({ label = "Loading approved portal data…" }: { label?: string }) {
  return <div className="ui-state ui-state-loading" role="status" aria-live="polite"><span className="state-spinner" aria-hidden="true" />{label}</div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="ui-state ui-state-empty"><span className="state-mark" aria-hidden="true">—</span><strong>{title}</strong><p>{description}</p></div>;
}

export function ErrorState({ title = "The portal could not load this view.", description, onRetry }: { title?: string; description: string; onRetry?: () => void }) {
  return <div className="ui-state ui-state-error" role="alert"><span className="state-mark" aria-hidden="true">!</span><strong>{title}</strong><p>{description}</p>{onRetry && <button className="secondary-button" onClick={onRetry}>Try again</button>}</div>;
}

export function SectionHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="section-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2>{description && <p className="muted">{description}</p>}</div>{action}</div>;
}
