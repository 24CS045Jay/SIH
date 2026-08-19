import { useEffect, useState } from "react";
import { AlertItem } from "../../types";
import { API, authHeaders } from "../../api/client";
import { REVIEWER_ROLES } from "../../types";

interface AlertCenterProps {
  token: string;
  userId: string;
  role: string;
}

export function AlertCenter({ token, userId, role }: AlertCenterProps) {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const params = new URLSearchParams();
    if (priority) params.set("priority", priority);
    if (status) params.set("status", status);
    const response = await fetch(`${API}/alerts?${params}`, {
      headers: authHeaders(token),
    });
    if (response.ok) setAlerts(await response.json());
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priority, status]);

  async function transition(alert: AlertItem, target: string) {
    const response = await fetch(`${API}/alerts/${alert.id}/transition`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({
        target,
        suggested_action: alert.suggested_action,
        suggested_department: alert.suggested_department,
      }),
    });
    const data = await response.json();
    setMessage(response.ok ? `Alert moved to ${target.replace("_", " ")}.` : (data.detail ?? "Transition rejected"));
    if (response.ok) load();
  }

  async function quickShare(alert: AlertItem) {
    const response = await fetch(`${API}/alerts/${alert.id}/quick-share`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({
        assignee_id: userId,
        excerpt: alert.source_excerpt || alert.title,
        summary: alert.title,
        action: alert.suggested_action || "Review and complete the proposed action",
        deadline: alert.deadline,
      }),
    });
    const data = await response.json();
    setMessage(
      response.ok
        ? "Quick Share routed the minimum necessary excerpt and action."
        : (data.detail ?? "Quick Share rejected")
    );
    if (response.ok) load();
  }

  async function createAction(alert: AlertItem) {
    const response = await fetch(`${API}/alerts/${alert.id}/create-action`, {
      method: "POST",
      headers: authHeaders(token),
    });
    const data = await response.json();
    setMessage(response.ok ? `Action ${data.id} created from alert.` : (data.detail ?? "Action creation rejected"));
  }

  return (
    <section className="workflow-center">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 4 — Operational Intelligence</p>
          <h2>Alert Center</h2>
          <p className="muted">
            Human approval is required before an alert can be assigned or converted into an action.
          </p>
        </div>
        <button className="export-button" onClick={() => exportCSV(alerts)}>
          Export CSV
        </button>
      </div>
      <div className="filter-row">
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["draft","needs_review","approved","assigned","acknowledged","in_progress","completed","verified_closed","rejected"].map(
            (s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>
          )}
        </select>
      </div>
      {message && <p className="success-message">{message}</p>}
      <div className="alert-list">
        {alerts.length === 0 ? (
          <div className="empty-state">
            <h3>No alerts in this queue</h3>
            <p>AI-derived priority signals will appear here for human verification.</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <article className={`alert-card priority-${alert.priority}`} key={alert.id}>
              <div className="alert-card-heading">
                <div>
                  <span className={`priority-label ${alert.priority}`}>{alert.priority}</span>
                  <h3>{alert.title}</h3>
                </div>
                <span className="status-badge">{alert.status.replaceAll("_", " ")}</span>
              </div>
              <p><strong>Reason:</strong> {alert.reason_codes.join(" · ") || "Review required"}</p>
              <p><strong>Suggested department:</strong> {alert.suggested_department || "Not specified"}</p>
              <p><strong>Suggested action:</strong> {alert.suggested_action || "Review source evidence"}</p>
              <p><strong>Deadline:</strong> {alert.deadline ? new Date(alert.deadline).toLocaleString() : "No deadline found"}</p>
              {alert.source_excerpt && <blockquote>{alert.source_excerpt}</blockquote>}
              <div className="workflow-actions">
                <button
                  className="secondary-button"
                  disabled={alert.status !== "draft"}
                  onClick={() => transition(alert, "needs_review")}
                >
                  Send to review
                </button>
                <button
                  className="primary-button"
                  disabled={alert.status !== "needs_review" || !REVIEWER_ROLES.has(role)}
                  onClick={() => transition(alert, "approved")}
                >
                  Approve
                </button>
                <button
                  className="secondary-button"
                  disabled={!["approved","assigned"].includes(alert.status)}
                  onClick={() => quickShare(alert)}
                >
                  Quick Share
                </button>
                <button
                  className="secondary-button"
                  disabled={!["approved","assigned"].includes(alert.status) || !REVIEWER_ROLES.has(role)}
                  onClick={() => createAction(alert)}
                >
                  Create action
                </button>
                <button className="text-button" onClick={() => transition(alert, "rejected")}>
                  Reject
                </button>
              </div>
              <div className="source-ref">Source version: {alert.source_version_id}</div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function exportCSV(alerts: AlertItem[]) {
  const header = ["ID","Title","Priority","Status","Department","Deadline","Reason codes"];
  const rows = alerts.map((a) => [
    a.id, a.title, a.priority, a.status,
    a.suggested_department ?? "",
    a.deadline ?? "",
    (a.reason_codes ?? []).join("; "),
  ]);
  const csv = [header, ...rows].map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "kmrl-alerts.csv";
  a.click();
  URL.revokeObjectURL(url);
}
