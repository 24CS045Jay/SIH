import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const navItems = ["Overview", "Documents", "Actions", "Alerts", "Audit log"];

function PortalLayout() {
  const [active, setActive] = useState("Overview");
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">K</div>
        <div><p className="eyebrow">Kochi Metro Rail Limited</p><h1>Document Intelligence &amp; Action Portal</h1></div>
        <div className="topbar-meta"><span className="env-badge">DEMO ENVIRONMENT</span><span className="user-chip">Reviewer workspace</span></div>
      </header>
      <div className="portal-grid">
        <nav className="left-nav" aria-label="Primary navigation"><p className="nav-label">Workspace</p>{navItems.map((item) => <button key={item} className={active === item ? "nav-item active" : "nav-item"} onClick={() => setActive(item)}>{item}</button>)}<div className="nav-footer"><p className="eyebrow">Access scope</p><strong>Reviewer</strong><span>Human approval required for critical actions.</span></div></nav>
        <main className="center-stream"><div className="page-heading"><div><p className="eyebrow">Operational workspace</p><h2>{active}</h2><p className="muted">Traceable, prioritized information for human review.</p></div><button className="primary-button">Upload document</button></div><section className="empty-state" aria-label="Empty center stream"><div className="empty-icon">01</div><h3>No {active.toLowerCase()} yet</h3><p>When approved demo documents are processed, their signals and workflow items will appear here.</p></section></main>
        <aside className="evidence-panel"><div className="panel-heading"><div><p className="eyebrow">Trust layer</p><h2>Evidence</h2></div><span className="status-dot">Awaiting selection</span></div><div className="evidence-empty"><strong>Select an item to inspect evidence</strong><p>Source document, page citation, confidence, and reviewer state will be shown here.</p></div><div className="synthetic-watermark">SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA.</div></aside>
      </div>
      <footer className="footer"><span>CHA-225 Phase 1 scaffold</span><span>All AI-derived fields will carry source, citation, confidence, and review state.</span></footer>
    </div>
  );
}

function App() {
  const isPublic = window.location.pathname === "/login";
  if (isPublic) return <div className="public-page"><div className="public-card"><p className="eyebrow">KMRL Document Intelligence</p><h1>Sign in to the reviewer portal</h1><p className="muted">Authentication and RBAC wiring will be introduced in the next phase.</p><button className="primary-button" onClick={() => { window.location.href = "/"; }}>Continue to demo workspace</button></div></div>;
  return <PortalLayout />;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
