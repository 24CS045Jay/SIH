import { useEffect, useState } from "react";
import { AnalyticsSummary, User } from "../../types";
import { API, authHeaders } from "../../api/client";

interface CentralControlProps {
  token: string;
  user: User;
}

/**
 * Module 1 — Central Control
 * Default landing screen for all roles. Shows processing status, critical signals,
 * priority distribution, and pending items.
 */
export function CentralControl({ token, user }: CentralControlProps) {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/analytics/summary`, { headers: authHeaders(token) })
      .then(async (r) => {
        if (r.ok) setSummary(await r.json());
        else {
          // Fallback: compute from individual endpoints if analytics route not yet deployed
          const [docsR, alertsR, actionsR] = await Promise.all([
            fetch(`${API}/documents`, { headers: authHeaders(token) }),
            fetch(`${API}/alerts`, { headers: authHeaders(token) }),
            fetch(`${API}/actions`, { headers: authHeaders(token) }),
          ]);
          const docs = docsR.ok ? await docsR.json() : [];
          const alerts = alertsR.ok ? await alertsR.json() : [];
          const actions = actionsR.ok ? await actionsR.json() : [];

          const byStatus = (arr: { status: string }[]) =>
            arr.reduce<Record<string, number>>((acc, item) => {
              acc[item.status] = (acc[item.status] ?? 0) + 1;
              return acc;
            }, {});

          const byPriority = (arr: { priority: string }[]) =>
            arr.reduce<Record<string, number>>((acc, item) => {
              acc[item.priority] = (acc[item.priority] ?? 0) + 1;
              return acc;
            }, {});

          const byDept = (arr: { suggested_department?: string | null }[]) =>
            arr.reduce<Record<string, number>>((acc, item) => {
              const d = item.suggested_department ?? "Unassigned";
              acc[d] = (acc[d] ?? 0) + 1;
              return acc;
            }, {});

          const now = Date.now();
          const overdueCount = actions.filter(
            (a: { due_at: string | null; status: string }) =>
              a.due_at &&
              new Date(a.due_at).getTime() < now &&
              !["completed", "closed", "rejected"].includes(a.status)
          ).length;

          setSummary({
            total_documents: docs.length,
            documents_by_status: byStatus(docs),
            total_alerts: alerts.length,
            alerts_by_priority: byPriority(alerts),
            alerts_by_department: byDept(alerts),
            total_actions: actions.length,
            actions_by_status: byStatus(actions),
            overdue_actions: overdueCount,
            avg_days_to_complete: null,
          });
        }
      })
      .catch(() => setError("Unable to load analytics. Check backend connectivity."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="center-stream"><p className="muted">Loading Central Control…</p></div>;
  if (error) return <div className="center-stream"><p className="form-error">{error}</p></div>;
  if (!summary) return null;

  const criticalAlerts = summary.alerts_by_priority["critical"] ?? 0;
  const highAlerts = summary.alerts_by_priority["high"] ?? 0;
  const pendingReview = summary.documents_by_status["review_ready"] ?? 0;
  const openActions = (summary.actions_by_status["open"] ?? 0) + (summary.actions_by_status["acknowledged"] ?? 0) + (summary.actions_by_status["in_progress"] ?? 0);

  const priorityOrder = ["critical", "high", "medium", "low"] as const;
  const priorityColors: Record<string, string> = {
    critical: "#b42318", high: "#c56a00", medium: "#9a6700", low: "#3d4590",
  };
  const maxAlert = Math.max(...Object.values(summary.alerts_by_priority), 1);
  const maxStatus = Math.max(...Object.values(summary.documents_by_status), 1);

  const deptEntries = Object.entries(summary.alerts_by_department)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);
  const maxDept = Math.max(...deptEntries.map(([, v]) => v), 1);

  return (
    <section className="dashboard">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 1</p>
          <h2>Central Control</h2>
          <p className="muted">
            Operational overview — processing status, priority signals, and pending workflows.
          </p>
        </div>
      </div>

      {/* KPI stat cards */}
      <div className="stat-grid">
        <div className={`stat-card ${criticalAlerts > 0 ? "critical" : "ok"}`}>
          <div className="stat-value">{criticalAlerts}</div>
          <div className="stat-label">Critical alerts</div>
          <div className="stat-sub">Require human approval</div>
        </div>
        <div className={`stat-card ${highAlerts > 0 ? "high" : "ok"}`}>
          <div className="stat-value">{highAlerts}</div>
          <div className="stat-label">High-priority alerts</div>
        </div>
        <div className={`stat-card ${summary.overdue_actions > 0 ? "warning" : "ok"}`}>
          <div className="stat-value">{summary.overdue_actions}</div>
          <div className="stat-label">Overdue actions</div>
          <div className="stat-sub">Past compliance deadline</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{pendingReview}</div>
          <div className="stat-label">Pending review</div>
          <div className="stat-sub">Documents ready for OCR review</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{openActions}</div>
          <div className="stat-label">Active actions</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{summary.total_documents}</div>
          <div className="stat-label">Total documents</div>
        </div>
      </div>

      {/* Alert priority distribution */}
      <div className="dashboard-section">
        <h3>Alert priority distribution</h3>
        <div className="bar-chart">
          {priorityOrder.map((p) => {
            const count = summary.alerts_by_priority[p] ?? 0;
            const pct = Math.round((count / maxAlert) * 100);
            return (
              <div className="bar-row" key={p}>
                <span className="bar-label" style={{ textTransform: "capitalize" }}>{p}</span>
                <div className="bar-track">
                  <div
                    className={`bar-fill ${p}`}
                    style={{ width: `${pct}%`, background: priorityColors[p] }}
                  />
                </div>
                <span className="bar-value">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Document processing pipeline */}
      <div className="dashboard-section">
        <h3>Document processing pipeline</h3>
        <div className="bar-chart">
          {["queued", "processing", "review_ready", "failed"].map((s) => {
            const count = summary.documents_by_status[s] ?? 0;
            const pct = Math.round((count / maxStatus) * 100);
            const colorClass = s === "failed" ? "critical" : s === "review_ready" ? "ok" : "";
            return (
              <div className="bar-row" key={s}>
                <span className="bar-label" style={{ textTransform: "capitalize" }}>
                  {s.replace("_", " ")}
                </span>
                <div className="bar-track">
                  <div className={`bar-fill ${colorClass}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="bar-value">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Department alert queue sizes */}
      {deptEntries.length > 0 && (
        <div className="dashboard-section">
          <h3>Alerts by department</h3>
          <div className="bar-chart">
            {deptEntries.map(([dept, count]) => {
              const pct = Math.round((count / maxDept) * 100);
              return (
                <div className="bar-row" key={dept}>
                  <span className="bar-label">{dept}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="bar-value">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action status summary */}
      <div className="dashboard-section">
        <h3>Action status summary</h3>
        <div className="bar-chart">
          {Object.entries(summary.actions_by_status).map(([s, count]) => {
            const maxAct = Math.max(...Object.values(summary.actions_by_status), 1);
            const pct = Math.round((count / maxAct) * 100);
            return (
              <div className="bar-row" key={s}>
                <span className="bar-label" style={{ textTransform: "capitalize" }}>
                  {s.replace("_", " ")}
                </span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="bar-value">{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
