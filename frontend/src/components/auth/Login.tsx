import { useEffect, useState } from "react";
import { User, roleLabels } from "../../types";
import { API as BASE, getDemoUsers } from "../../api/client";

interface LoginProps {
  onLogin: (user: User, token: string) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState("");
  const [password, setPassword] = useState("demo-password");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getDemoUsers()
      .then((items) => {
        setUsers(items);
        if (items[0]) setSelected(items[0].email);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load demo users.");
      });
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: selected, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Login failed");
      onLogin(data.user, data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="public-page">
      <form className="public-card login-card" onSubmit={submit}>
        <span className="env-badge dark-badge">DEMO LOGIN</span>
        <p className="eyebrow">KMRL Document Intelligence</p>
        <h1>Sign in to the portal</h1>
        <p className="muted">
          Use a seeded role to preview document access. This is not production authentication.
        </p>
        <label>
          Demo user
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {users.map((user) => (
              <option key={user.id} value={user.email}>
                {user.name} — {roleLabels[user.role]}
                {user.department ? ` — ${user.department}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Password
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary-button full-width" disabled={busy || !selected}>
          {busy ? "Signing in…" : "Continue with demo login"}
        </button>
      </form>
    </div>
  );
}
