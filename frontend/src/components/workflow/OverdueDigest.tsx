import { useEffect, useState } from "react";
import { ActionItem } from "../../types";
import { API, authHeaders } from "../../api/client";

interface OverdueDigestProps {
  token: string;
}

/**
 * Overdue Digest — lists all actions past their due date, sorted by most overdue.
 * This is a dedicated compliance deadline view separate from the main Action Center filter.
 */
export function OverdueDigest({ token }: OverdueDigestProps) {
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/actions?overdue=true`, { headers: authHeaders(token) })
      .then(async (r) => { if (r.ok) setActions(await r.json()); })
      .finally(() => setLoading(false));
  }, [token]);

  function daysPastDue(dueAt: string | null): number {
    if (!dueAt) return 0;
    const ms = Date.now() - new Date(dueAt).getTime();
    return Math.max(0, Math.floor(ms / 86_400_000));
  }

  const sorted = [...actions].sort((a, b) => daysPastDue(b.due_at) - daysPastDue(a.due_at));

  return (
    <section className="workflow-center">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 4 — Compliance deadline monitor</p>
          <h2>Overdue Digest</h2>
          <p className="muted">
            Actions past their due date, sorted by most overdue. Each requires owner attention or
            escalation.
          </p>
        </div>
      </div>
      {loading && <p className="muted">Loading overdue actions…</p>}
      {!loading && sorted.length === 0 && (
        <div className="empty-state">
          <h3>No overdue actions</h3>
          <p>All actions are within their compliance deadlines.</p>
        </div>
      )}
      <div className="overdue-digest">
        {sorted.map((action) => {
          const days = daysPastDue(action.due_at);
          return (
            <div className="overdue-row" key={action.id}>
              <div>
                <strong>{action.title}</strong>
                <span className="signal-meta">
                  Owner: {action.owner_id || "Unassigned"} · Priority: {action.priority}
                </span>
              </div>
              <span className={`priority-label ${action.priority}`}>{action.priority}</span>
              <span className="status-badge">{action.status.replaceAll("_", " ")}</span>
              <span className="overdue-days">{days}d overdue</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
