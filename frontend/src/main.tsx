import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type User = { id: string; name: string; email: string; role: string; department: string | null; department_id?: string | null };
const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "kmrl_demo_access_token";
const USER_KEY = "kmrl_demo_user";
const roleLabels: Record<string, string> = {
  system_administrator: "System Administrator",
  document_administrator: "Document Administrator",
  reviewer: "Reviewer",
  department_user: "Department User",
  executive_viewer: "Executive Viewer",
  auditor: "Auditor",
};
const landingByRole: Record<string, { title: string; description: string; view: string }> = {
  system_administrator: { title: "Administration overview", description: "Manage portal access, departments, and operational controls.", view: "Admin control center" },
  document_administrator: { title: "Document operations", description: "Oversee ingestion, classification, and document processing queues.", view: "Document administration" },
  reviewer: { title: "Review workspace", description: "Approve AI-derived actions with source evidence and confidence context.", view: "Human verification queue" },
  department_user: { title: "Department action queue", description: "Track alerts and actions routed to your department.", view: "Department queue" },
  executive_viewer: { title: "Executive summary", description: "Review high-level operational signals, priorities, and workflow health.", view: "Summary dashboard" },
  auditor: { title: "Audit log", description: "Inspect append-only traceability across document and action workflows.", view: "Audit evidence" },
};

async function getDemoUsers(): Promise<User[]> { const response = await fetch(`${API}/auth/demo-users`); if (!response.ok) throw new Error("Demo users unavailable"); return response.json(); }

function Login({ onLogin }: { onLogin: (user: User, token: string) => void }) {
  const [users, setUsers] = useState<User[]>([]); const [selected, setSelected] = useState(""); const [password, setPassword] = useState("demo-password"); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { getDemoUsers().then((items) => { setUsers(items); if (items[0]) setSelected(items[0].email); }).catch(() => setError("Start the backend and seed the demo users first.")); }, []);
  const selectedUser = users.find((user) => user.email === selected);
  async function submit(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: selected, password }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Login failed"); onLogin(data.user, data.access_token); } catch (err) { setError(err instanceof Error ? err.message : "Login failed"); } finally { setBusy(false); } }
  return <div className="public-page"><form className="public-card login-card" onSubmit={submit}><span className="env-badge dark-badge">DEMO LOGIN</span><p className="eyebrow">KMRL Document Intelligence</p><h1>Sign in to the reviewer portal</h1><p className="muted">Use a seeded demo role to preview role-aware access. This is not production authentication.</p><label>Demo user<select value={selected} onChange={(event) => setSelected(event.target.value)}>{users.map((user) => <option key={user.id} value={user.email}>{user.name} — {roleLabels[user.role]}{user.department ? ` — ${user.department}` : ""}</option>)}</select></label><label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" /></label>{selectedUser && <div className="login-preview"><strong>{roleLabels[selectedUser.role]}</strong><span>{selectedUser.department ?? "Cross-department access"}</span></div>}{error && <p className="form-error">{error}</p>}<button className="primary-button full-width" disabled={busy || !selected}>{busy ? "Signing in…" : "Continue with demo login"}</button></form></div>;
}

function PortalLayout({ user, token, onLogout }: { user: User; token: string; onLogout: () => void }) {
  const landing = landingByRole[user.role] ?? landingByRole.reviewer; const [active, setActive] = useState(landing.title); const [menuOpen, setMenuOpen] = useState(false); const [apiMessage, setApiMessage] = useState("");
  const navItems = useMemo(() => [landing.title, "Documents", "Actions", "Alerts", "Evidence", "Audit log"], [landing.title]);
  async function checkIdentity() { const response = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } }); const data = await response.json(); setApiMessage(response.ok ? `Verified API identity: ${data.name}` : data.detail ?? "Authorization check failed"); }
  async function logout() { await fetch(`${API}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => undefined); onLogout(); }
  return <div className="app-shell"><header className="topbar"><div className="brand-mark" aria-hidden="true">K</div><div><p className="eyebrow">Kochi Metro Rail Limited</p><h1>Document Intelligence &amp; Action Portal</h1></div><div className="topbar-meta"><span className="env-badge">DEMO ENVIRONMENT</span><div className="user-menu-wrap"><button className="user-chip user-button" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen}>{user.name} ▾</button>{menuOpen && <div className="user-menu"><strong>Logged in as</strong><span>{user.name}</span><span>{roleLabels[user.role]}</span><span>{user.department ?? "Cross-department"}</span><button onClick={logout}>Log out</button></div>}</div></div></header><div className="identity-strip"><strong>Logged in as {user.name}</strong><span>— {roleLabels[user.role]} — {user.department ?? "Cross-department access"}</span></div><div className="portal-grid"><nav className="left-nav" aria-label="Primary navigation"><p className="nav-label">Workspace</p>{navItems.map((item) => <button key={item} className={active === item ? "nav-item active" : "nav-item"} onClick={() => setActive(item)}>{item}</button>)}<div className="nav-footer"><p className="eyebrow">Access scope</p><strong>{roleLabels[user.role]}</strong><span>Permissions are enforced by the API for every protected operation.</span></div></nav><main className="center-stream"><div className="page-heading"><div><p className="eyebrow">Role-aware workspace</p><h2>{active}</h2><p className="muted">{active === landing.title ? landing.description : "Traceable, prioritized information for human review."}</p></div><button className="primary-button" onClick={checkIdentity}>Verify API identity</button></div><section className="role-landing"><div className="empty-icon">{user.role.slice(0, 2).toUpperCase()}</div><h3>{landing.view}</h3><p>{landing.description}</p><div className="role-callout"><strong>RBAC enabled</strong><span>Your token carries role and department claims. Protected endpoints return HTTP 403 when your role is not authorized.</span></div>{apiMessage && <p className="success-message">{apiMessage}</p>}</section></main><aside className="evidence-panel"><div className="panel-heading"><div><p className="eyebrow">Trust layer</p><h2>Evidence</h2></div><span className="status-dot">Awaiting selection</span></div><div className="evidence-empty"><strong>Select an item to inspect evidence</strong><p>Source document, page citation, confidence, and reviewer state will be shown here.</p></div><div className="synthetic-watermark">SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA.</div></aside></div><footer className="footer"><span>CHA-225 Phase 3 scaffold</span><span>AI-derived fields require human review and source traceability.</span></footer></div>;
}

function App() { const [user, setUser] = useState<User | null>(() => { const raw = localStorage.getItem(USER_KEY); return raw ? JSON.parse(raw) : null; }); const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) ?? ""); function onLogin(nextUser: User, nextToken: string) { localStorage.setItem(USER_KEY, JSON.stringify(nextUser)); localStorage.setItem(TOKEN_KEY, nextToken); setUser(nextUser); setToken(nextToken); } function onLogout() { localStorage.removeItem(USER_KEY); localStorage.removeItem(TOKEN_KEY); setUser(null); setToken(""); } return user && token ? <PortalLayout user={user} token={token} onLogout={onLogout} /> : <Login onLogin={onLogin} />; }

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
