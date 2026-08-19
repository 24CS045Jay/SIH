import { useEffect, useState } from "react";
import { AuditEventItem } from "../../types";
import { API, authHeaders } from "../../api/client";

interface AuditLogViewerProps {
  token: string;
}

export function AuditLogViewer({ token }: AuditLogViewerProps) {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actorFilter, setActorFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [fromDate, setFromDate] = useState("");

  async function load() {
    const params = new URLSearchParams();
    if (actorFilter) params.set("actor_id", actorFilter);
    if (typeFilter) params.set("event_type", typeFilter);
    if (fromDate) params.set("from_date", fromDate);
    setLoading(true);
    try {
      const response = await fetch(`${API}/audit/events?${params}`, {
        headers: authHeaders(token),
      });
      if (response.ok) setEvents(await response.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [token, actorFilter, typeFilter, fromDate]); // eslint-disable-line react-hooks/exhaustive-deps

  function exportCSV() {
    const header = ["ID","Timestamp","Actor ID","Event type","Object type","Object ID","Hash"];
    const rows = events.map((e) => [
      e.id, e.timestamp, e.actor_id ?? "", e.event_type, e.object_type, e.object_id, e.hash,
    ]);
    const csv = [header, ...rows]
      .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "kmrl-audit-log.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  // Unique event types for filter dropdown
  const eventTypes = Array.from(new Set(events.map((e) => e.event_type))).sort();

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <p className="eyebrow" style={{ margin: 0 }}>Append-only audit trail</p>
        <button className="export-button" onClick={exportCSV}>Export CSV</button>
      </div>
      <div className="audit-filters">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by event type"
        >
          <option value="">All event types</option>
          {eventTypes.map((t) => (
            <option key={t} value={t}>{t.replaceAll("_", " ")}</option>
          ))}
        </select>
        <input
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
          aria-label="From date"
        />
      </div>
      {loading && <p className="muted">Loading audit log…</p>}
      {!loading && events.length === 0 && (
        <div className="empty-state">
          <h3>No audit events found</h3>
          <p>Audit events are recorded automatically for every document and workflow action.</p>
        </div>
      )}
      {!loading && events.length > 0 && (
        <div className="audit-table-wrap">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event type</th>
                <th>Object type</th>
                <th>Object ID</th>
                <th>Actor ID</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.timestamp).toLocaleString()}</td>
                  <td>{e.event_type.replaceAll("_", " ")}</td>
                  <td>{e.object_type}</td>
                  <td title={e.object_id}>{e.object_id.slice(0, 12)}…</td>
                  <td title={e.actor_id ?? ""}>{e.actor_id ? e.actor_id.slice(0, 12) + "…" : "—"}</td>
                  <td title={e.hash}>{e.hash.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
