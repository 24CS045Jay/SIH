import { useState } from "react";
import { AdminPanel } from "../components/admin/AdminPanel";
import { AuditLogViewer } from "../components/audit/AuditLogViewer";

interface Module6PageProps {
  token: string;
  role: string;
}

type M6View = "admin" | "audit";

/**
 * Module 6 — Administration & Governance
 * Admin Panel (system_administrator only) + Audit Log viewer (system_administrator + auditor).
 * The entire module is only mounted for these two roles (LeftNav hides it for others).
 */
export function Module6Page({ token, role }: Module6PageProps) {
  const isSysAdmin = role === "system_administrator";
  const [view, setView] = useState<M6View>(isSysAdmin ? "admin" : "audit");

  return (
    <div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 6</p>
          <h2>Administration &amp; Governance</h2>
          <p className="muted">
            User access, department taxonomy, read-only system config, and append-only
            audit trail.
          </p>
        </div>
      </div>

      <div className="module-tabs" role="tablist" style={{ marginBottom: 24 }}>
        {isSysAdmin && (
          <button
            className={`module-tab ${view === "admin" ? "active" : ""}`}
            onClick={() => setView("admin")}
            role="tab"
            aria-selected={view === "admin"}
          >
            Administration
          </button>
        )}
        <button
          className={`module-tab ${view === "audit" ? "active" : ""}`}
          onClick={() => setView("audit")}
          role="tab"
          aria-selected={view === "audit"}
        >
          Audit Log
        </button>
      </div>

      {view === "admin" && isSysAdmin && <AdminPanel token={token} />}
      {view === "audit" && <AuditLogViewer token={token} />}
    </div>
  );
}
