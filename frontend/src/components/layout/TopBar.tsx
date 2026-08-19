import { useEffect, useState } from "react";
import { User } from "../../types";
import { API, TOKEN_KEY, THEME_KEY, authHeaders } from "../../api/client";
import { roleLabels } from "../../types";
import { ToastNotification } from "../notifications/ToastNotification";

interface TopBarProps {
  user: User;
  token: string;
  onLogout: () => void;
}

export function TopBar({ user, token, onLogout }: TopBarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"indigo" | "emerald">(() => {
    return (localStorage.getItem(THEME_KEY) as "indigo" | "emerald") ?? "indigo";
  });

  // Apply theme to <html> element on mount and change
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((prev) => (prev === "indigo" ? "emerald" : "indigo"));
  }

  async function logout() {
    await fetch(`${API}/auth/logout`, {
      method: "POST",
      headers: authHeaders(token),
    }).catch(() => undefined);
    onLogout();
  }

  return (
    <header className="topbar">
      <div className="brand-mark">K</div>
      <div className="brand-block">
        <p className="eyebrow">Kochi Metro Rail Limited</p>
        <h1>Document Intelligence &amp; Action Portal</h1>
        <p className="brand-tagline">
          Ingest → Understand → Search → Detect Changes → Act → Govern
        </p>
      </div>
      <div className="topbar-meta">
        <span className="env-badge">DEMO ENVIRONMENT</span>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          title={`Switch to ${theme === "indigo" ? "Slate & Emerald" : "Deep Indigo & Amber"} theme`}
          aria-label="Toggle colour theme"
        >
          {theme === "indigo" ? "⬡ INDIGO" : "◈ EMERALD"}
        </button>
        <div className="user-menu-wrap">
          <button
            className="user-chip user-button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            {user.name} ▾
          </button>
          {menuOpen && (
            <div className="user-menu" role="menu">
              <strong>Logged in as</strong>
              <span>{user.name}</span>
              <span>{roleLabels[user.role]}</span>
              <span>{user.department ?? "Cross-department"}</span>
              <button onClick={logout}>Log out</button>
            </div>
          )}
        </div>
      </div>
      <ToastNotification token={token} />
    </header>
  );
}
