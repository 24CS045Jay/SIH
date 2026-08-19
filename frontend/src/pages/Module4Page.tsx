import { useState } from "react";
import { AlertCenter } from "../components/workflow/AlertCenter";
import { ActionCenter } from "../components/workflow/ActionCenter";
import { OverdueDigest } from "../components/workflow/OverdueDigest";

interface Module4PageProps {
  token: string;
  userId: string;
  role: string;
}

type M4View = "alerts" | "actions" | "overdue";

/**
 * Module 4 — Actions & Operational Intelligence
 * Alert Center + Action Center + Overdue Digest as a single module with sub-tabs.
 * Alert → Action is one continuous flow, not two separate nav items.
 */
export function Module4Page({ token, userId, role }: Module4PageProps) {
  const [view, setView] = useState<M4View>("alerts");

  return (
    <div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 4</p>
          <h2>Actions &amp; Operational Intelligence</h2>
          <p className="muted">
            Alerts surface AI-derived findings; human approval converts them into owned,
            trackable actions. Overdue view monitors compliance deadlines.
          </p>
        </div>
      </div>

      <div className="module-tabs" role="tablist" style={{ marginBottom: 24 }}>
        <button
          className={`module-tab ${view === "alerts" ? "active" : ""}`}
          onClick={() => setView("alerts")}
          role="tab"
          aria-selected={view === "alerts"}
        >
          Alerts
        </button>
        <button
          className={`module-tab ${view === "actions" ? "active" : ""}`}
          onClick={() => setView("actions")}
          role="tab"
          aria-selected={view === "actions"}
        >
          Actions
        </button>
        <button
          className={`module-tab ${view === "overdue" ? "active" : ""}`}
          onClick={() => setView("overdue")}
          role="tab"
          aria-selected={view === "overdue"}
        >
          Overdue Digest
        </button>
      </div>

      {view === "alerts" && (
        <AlertCenter token={token} userId={userId} role={role} />
      )}
      {view === "actions" && (
        <ActionCenter token={token} userId={userId} role={role} />
      )}
      {view === "overdue" && (
        <OverdueDigest token={token} />
      )}
    </div>
  );
}
