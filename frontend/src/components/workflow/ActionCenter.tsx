import { useEffect, useState } from "react";
import { ActionItem } from "../../types";
import { API, authHeaders } from "../../api/client";
import { REVIEWER_ROLES } from "../../types";
import { ActionTimeline } from "./ActionTimeline";

interface ActionCenterProps {
  token: string;
  userId: string;
  role: string;
}

export function ActionCenter({ token, userId, role }: ActionCenterProps) {
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [status, setStatus] = useState("");
  const [overdue, setOverdue] = useState(false);
  const [selected, setSelected] = useState<ActionItem | null>(null);
  const [message, setMessage] = useState("");

  async function load() {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (overdue) params.set("overdue", "true");
    const response = await fetch(`${API}/actions?${params}`, {
      headers: authHeaders(token),
    });
    if (response.ok) setActions(await response.json());
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, overdue]);

  async function move(action: ActionItem, target: string, evidence?: string) {
    const response = await fetch(`${API}/actions/${action.id}/transition`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({
        target,
        detail: `Moved from Action Center to ${target}`,
        completion_evidence: evidence,
      }),
    });
    const data = await response.json();
    setMessage(
      response.ok
        ? `Action moved to ${target.replaceAll("_", " ")}.`
        : (data.detail ?? "Action transition rejected")
    );
    if (response.ok) {
      setSelected(data);
      load();
    }
  }

  async function update(action: ActionItem) {
    const response = await fetch(`${API}/actions/${action.id}`, {
      method: "PATCH",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ comments: `${action.comments} Updated from Action Center.` }),
    });
    const data = await response.json();
    setMessage(
      response.ok
        ? "Action comments saved and timeline updated."
        : (data.detail ?? "Action update rejected")
    );
    if (response.ok) {
      setSelected(data);
      load();
    }
  }

  const canAct = (action: ActionItem) =>
    action.owner_id === userId || REVIEWER_ROLES.has(role);

  return (
    <section className="workflow-center">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 4 — Operational Intelligence</p>
          <h2>Action Center</h2>
          <p className="muted">
            Owners acknowledge and complete actions; Reviewers verify and close them.
          </p>
        </div>
        <button className="export-button" onClick={() => exportCSV(actions)}>
          Export CSV
        </button>
      </div>
      <div className="filter-row">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All action statuses</option>
          {["draft","open","acknowledged","in_progress","blocked","overdue","completed","closed","rejected"].map(
            (s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>
          )}
        </select>
        <label className="check-filter">
          <input
            type="checkbox"
            checked={overdue}
            onChange={(e) => setOverdue(e.target.checked)}
          />{" "}
          Overdue only
        </label>
      </div>
      {message && <p className="success-message">{message}</p>}
      <div className="action-list">
        {actions.length === 0 ? (
          <div className="empty-state">
            <h3>No actions in this queue</h3>
            <p>Approved alerts can be converted into owned actions.</p>
          </div>
        ) : (
          actions.map((action) => (
            <article className={`action-card ${action.status}`} key={action.id}>
              <div className="alert-card-heading">
                <div>
                  <span className={`priority-label ${action.priority}`}>{action.priority}</span>
                  <h3>{action.title}</h3>
                </div>
                <span className="status-badge">{action.status.replaceAll("_", " ")}</span>
              </div>
              <p><strong>Owner:</strong> {action.owner_id || "Unassigned"}</p>
              <p><strong>Due:</strong> {action.due_at ? new Date(action.due_at).toLocaleString() : "No due date"}</p>
              {action.comments && <p><strong>Comments:</strong> {action.comments}</p>}
              {action.status === "overdue" && (
                <span className="overdue-flag">Overdue — in-app reminder flag only</span>
              )}
              <div className="workflow-actions">
                <button
                  className="secondary-button"
                  disabled={!canAct(action)}
                  onClick={() => move(action, "acknowledged")}
                >
                  Acknowledge
                </button>
                <button
                  className="secondary-button"
                  disabled={!canAct(action)}
                  onClick={() => move(action, "in_progress")}
                >
                  Start work
                </button>
                <button
                  className="primary-button"
                  disabled={!canAct(action)}
                  onClick={() => move(action, "completed", "Completion evidence recorded in the demo workflow.")}
                >
                  Complete
                </button>
                <button
                  className="secondary-button"
                  disabled={action.status !== "completed" || !REVIEWER_ROLES.has(role)}
                  onClick={() => move(action, "closed")}
                >
                  Verify and close
                </button>
                <button
                  className="text-button"
                  onClick={() => { setSelected(action); update(action); }}
                >
                  Save comment
                </button>
              </div>
              <button
                className="timeline-toggle"
                onClick={() => setSelected(selected?.id === action.id ? null : action)}
              >
                View status timeline
              </button>
              {selected?.id === action.id && <ActionTimeline events={selected.events} />}
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function exportCSV(actions: ActionItem[]) {
  const header = ["ID","Title","Priority","Status","Owner","Due date","Comments"];
  const rows = actions.map((a) => [
    a.id, a.title, a.priority, a.status,
    a.owner_id ?? "", a.due_at ?? "", a.comments,
  ]);
  const csv = [header, ...rows].map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const el = document.createElement("a");
  el.href = url; el.download = "kmrl-actions.csv"; el.click();
  URL.revokeObjectURL(url);
}
