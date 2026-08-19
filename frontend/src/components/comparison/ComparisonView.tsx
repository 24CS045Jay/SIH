import { useEffect, useState } from "react";
import { ComparisonItem, ChangeItem } from "../../types";
import { API, authHeaders } from "../../api/client";
import { REVIEWER_ROLES } from "../../types";

interface ComparisonViewProps {
  token: string;
  role: string;
}

export function ComparisonView({ token, role }: ComparisonViewProps) {
  const [comparisons, setComparisons] = useState<ComparisonItem[]>([]);
  const [selected, setSelected] = useState<ComparisonItem | null>(null);
  const [message, setMessage] = useState("");

  async function load() {
    const response = await fetch(`${API}/comparisons`, { headers: authHeaders(token) });
    if (response.ok) setComparisons(await response.json());
  }

  useEffect(() => { load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function openComparison(id: string) {
    const response = await fetch(`${API}/comparisons/${id}`, { headers: authHeaders(token) });
    if (response.ok) setSelected(await response.json());
  }

  async function convert(change: ChangeItem) {
    if (!selected) return;
    const response = await fetch(
      `${API}/comparisons/${selected.id}/changes/${change.id}/action`,
      { method: "POST", headers: authHeaders(token) }
    );
    const data = await response.json();
    setMessage(
      response.ok
        ? "Draft action candidate created. A reviewer must verify it in Action Center."
        : (data.detail ?? "Conversion rejected")
    );
    if (response.ok)
      setSelected((c) =>
        c
          ? { ...c, changes: c.changes.map((ch) => ch.id === change.id ? { ...ch, action_id: data.action_id } : ch) }
          : c
      );
  }

  if (!selected)
    return (
      <section className="comparison-workspace">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Module 5 — Changes &amp; Version Intelligence</p>
            <h2>What's Changed?</h2>
            <p className="muted">
              Select an approved version comparison to review aligned additions, deletions, and
              modified obligations.
            </p>
          </div>
        </div>
        {comparisons.length === 0 ? (
          <div className="empty-state">
            <h3>No comparisons available</h3>
            <p>Upload a new version of an existing document to generate a comparison after OCR.</p>
          </div>
        ) : (
          <div className="comparison-list">
            {comparisons.map((item) => (
              <button
                className="comparison-row"
                key={item.id}
                onClick={() => openComparison(item.id)}
              >
                <span>
                  <strong>
                    {item.old_title || "Previous version"} → {item.new_title || "New version"}
                  </strong>
                  <small>
                    {item.old_version_id.slice(0, 8)} → {item.new_version_id.slice(0, 8)}
                  </small>
                </span>
                <span className="status-badge">
                  {item.changes.length} changes · {item.status}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>
    );

  return (
    <section className="comparison-workspace">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 5 — Aligned document diff</p>
          <h2>What's Changed?</h2>
          <p className="muted">
            {selected.old_title || "Previous version"} → {selected.new_title || "New version"} ·{" "}
            {selected.changes.length} detected changes
          </p>
        </div>
        <button className="secondary-button" onClick={() => setSelected(null)}>
          All comparisons
        </button>
      </div>
      {message && <p className="success-message">{message}</p>}
      <div className="comparison-change-list">
        {selected.changes.map((change, index) => (
          <details className={`change-card change-${change.change_type}`} key={change.id} open>
            <summary>
              <span className="change-number">{index + 1}</span>
              <strong>{change.change_type.replaceAll("_", " ")}</strong>
              <span className={`priority-label ${change.priority}`}>{change.priority}</span>
              <span className="status-badge">{change.impact}</span>
            </summary>
            <div className="diff-grid">
              <div className="diff-pane old">
                <span className="eyebrow">Old text · p.{change.old_span?.page_no ?? "—"}</span>
                <p>{change.old_span?.quote || "No previous text — addition"}</p>
                {selected.old_document_id && (
                  <a
                    href={`${API}/documents/${selected.old_document_id}/source`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open old original
                  </a>
                )}
              </div>
              <div className="diff-pane new">
                <span className="eyebrow">New text · p.{change.new_span?.page_no ?? "—"}</span>
                <p>{change.new_span?.quote || "Text removed in new version"}</p>
                {selected.new_document_id && (
                  <a
                    href={`${API}/documents/${selected.new_document_id}/source`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open new original
                  </a>
                )}
              </div>
            </div>
            <div className="change-explanation">
              <p><strong>Interpretation:</strong> {change.interpretation}</p>
              <p><strong>Affected department:</strong> {change.affected_department || "Review required"}</p>
              <p><strong>Required action:</strong> {change.required_action || "Review the changed text"}</p>
              <button
                className="primary-button"
                disabled={!REVIEWER_ROLES.has(role) || Boolean(change.action_id)}
                onClick={() => convert(change)}
              >
                {change.action_id ? "Draft action created" : "Convert to reviewable action"}
              </button>
              {change.action_id && (
                <span className="muted">
                  Action candidate {change.action_id.slice(0, 8)} — human verification required.
                </span>
              )}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
