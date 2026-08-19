import { useEffect, useState } from "react";
import { User, DepartmentItem, roleLabels } from "../../types";
import { API, authHeaders } from "../../api/client";

interface AdminPanelProps {
  token: string;
}

type AdminTab = "users" | "departments" | "config";

/**
 * Admin Panel — System Administrator only.
 * Manages users/roles, departments, and shows read-only system config.
 */
export function AdminPanel({ token }: AdminPanelProps) {
  const [tab, setTab] = useState<AdminTab>("users");
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [newDeptName, setNewDeptName] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${API}/auth/demo-users`, { headers: authHeaders(token) })
      .then((r) => r.ok ? r.json() : [])
      .then(setUsers);
    fetch(`${API}/admin/departments`, { headers: authHeaders(token) })
      .then((r) => r.ok ? r.json() : [])
      .then(setDepartments);
    fetch(`${API}/admin/config`, { headers: authHeaders(token) })
      .then((r) => r.ok ? r.json() : {})
      .then(setConfig);
  }, [token]);

  async function updateUserRole(userId: string, role: string) {
    const response = await fetch(`${API}/admin/users/${userId}/role`, {
      method: "PATCH",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    const data = await response.json();
    setMessage(response.ok ? "Role updated." : (data.detail ?? "Update failed"));
    if (response.ok) {
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role } : u));
    }
  }

  async function addDepartment() {
    if (!newDeptName.trim()) return;
    const response = await fetch(`${API}/admin/departments`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ name: newDeptName.trim() }),
    });
    const data = await response.json();
    setMessage(response.ok ? "Department added." : (data.detail ?? "Add failed"));
    if (response.ok) {
      setDepartments((prev) => [...prev, data]);
      setNewDeptName("");
    }
  }

  return (
    <div>
      <div className="module-tabs" role="tablist">
        {(["users", "departments", "config"] as AdminTab[]).map((t) => (
          <button
            key={t}
            className={`module-tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
            role="tab"
            aria-selected={tab === t}
          >
            {t === "users" ? "Access & Roles" : t === "departments" ? "Departments & Routing" : "System Config"}
          </button>
        ))}
      </div>
      {message && <p className="success-message">{message}</p>}

      {tab === "users" && (
        <div className="admin-section">
          <div className="admin-section-header">
            <h3>User management</h3>
            <span className="muted" style={{ fontSize: 11 }}>{users.length} active users</span>
          </div>
          <div className="admin-section-body">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Department</th>
                  <th>Role</th>
                  <th>Change role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>{u.email}</td>
                    <td>{u.department ?? "—"}</td>
                    <td><span className="status-badge">{roleLabels[u.role] ?? u.role}</span></td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => updateUserRole(u.id, e.target.value)}
                        aria-label={`Role for ${u.name}`}
                      >
                        {Object.entries(roleLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "departments" && (
        <div className="admin-section">
          <div className="admin-section-header">
            <h3>Department taxonomy</h3>
          </div>
          <div className="admin-section-body">
            <div className="dept-tree">
              {departments.map((d) => (
                <div key={d.id} className={`dept-node ${d.parent_id ? "child" : ""}`}>
                  <span>{d.name}</span>
                  <span className="muted" style={{ fontSize: 10 }}>{d.id.slice(0, 8)}</span>
                </div>
              ))}
            </div>
            <div className="dept-add-form">
              <input
                placeholder="New department name"
                value={newDeptName}
                onChange={(e) => setNewDeptName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addDepartment()}
              />
              <button className="primary-button" onClick={addDepartment}>
                Add department
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === "config" && (
        <div className="admin-section">
          <div className="admin-section-header">
            <h3>System configuration (read-only, non-secret values)</h3>
          </div>
          <div className="admin-section-body">
            <div className="config-grid">
              {Object.entries(config).map(([key, value]) => (
                <div className="config-row" key={key}>
                  <span className="config-key">{key}</span>
                  <span className="config-val">{String(value)}</span>
                </div>
              ))}
              {Object.keys(config).length === 0 && (
                <p className="muted">Config endpoint not available.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
