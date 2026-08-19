import { roleLabels } from "../../types";

interface LeftNavProps {
  userName: string;
  userRole: string;
  active: string;
  onNavigate: (item: string) => void;
}

// The six modules in exact pitch order (Part 6)
const MODULE_NAV = [
  { id: "module1", label: "Module 1 — Central Control" },
  { id: "module2", label: "Module 2 — Document Intake & Processing" },
  { id: "module3", label: "Module 3 — Document Network & Intelligence" },
  { id: "module4", label: "Module 4 — Actions & Operational Intelligence" },
  { id: "module5", label: "Module 5 — Changes & Version Intelligence" },
  { id: "module6", label: "Module 6 — Administration & Governance" },
];

// Role visibility rules for Module 6 (admin+audit only)
const MODULE6_ROLES = new Set(["system_administrator", "auditor"]);

export function LeftNav({ userName, userRole, active, onNavigate }: LeftNavProps) {
  const visibleNav = MODULE_NAV.filter((item) => {
    if (item.id === "module6") return MODULE6_ROLES.has(userRole);
    return true;
  });

  return (
    <nav className="left-nav" aria-label="Module navigation">
      <p className="nav-label">Workspace</p>
      {visibleNav.map((item) => (
        <button
          key={item.id}
          className={active === item.id ? "nav-item active" : "nav-item"}
          onClick={() => onNavigate(item.id)}
          aria-current={active === item.id ? "page" : undefined}
        >
          {item.label}
        </button>
      ))}
      <div className="nav-footer">
        <p className="eyebrow">Access scope</p>
        <strong>{roleLabels[userRole]}</strong>
        <span>Protected API permissions apply to every operation.</span>
      </div>
    </nav>
  );
}
