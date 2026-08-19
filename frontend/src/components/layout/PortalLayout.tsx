import { useState } from "react";
import { User } from "../../types";
import { TopBar } from "./TopBar";
import { LeftNav } from "./LeftNav";
import { EvidencePanel } from "./EvidencePanel";
import { Module1Page } from "../../pages/Module1Page";
import { Module2Page } from "../../pages/Module2Page";
import { Module3Page } from "../../pages/Module3Page";
import { Module4Page } from "../../pages/Module4Page";
import { Module5Page } from "../../pages/Module5Page";
import { Module6Page } from "../../pages/Module6Page";

interface PortalLayoutProps {
  user: User;
  token: string;
  onLogout: () => void;
}

// Default landing module per role (always Module 1 — Central Control now)
function defaultModule(_role: string): string {
  return "module1";
}

export function PortalLayout({ user, token, onLogout }: PortalLayoutProps) {
  const [active, setActive] = useState<string>(() => defaultModule(user.role));

  function renderCenter() {
    switch (active) {
      case "module1": return <Module1Page token={token} user={user} />;
      case "module2": return <Module2Page token={token} role={user.role} />;
      case "module3": return <Module3Page token={token} role={user.role} />;
      case "module4": return <Module4Page token={token} userId={user.id} role={user.role} />;
      case "module5": return <Module5Page token={token} role={user.role} />;
      case "module6": return <Module6Page token={token} role={user.role} />;
      default:        return <Module1Page token={token} user={user} />;
    }
  }

  return (
    <div className="app-shell">
      <TopBar user={user} token={token} onLogout={onLogout} />
      <div className="identity-strip">
        <strong>Logged in as {user.name}</strong>
        <span> — {user.role.replace(/_/g, " ")} — {user.department ?? "Cross-department access"}</span>
      </div>
      <div className="portal-grid">
        <LeftNav
          userName={user.name}
          userRole={user.role}
          active={active}
          onNavigate={setActive}
        />
        <main className="center-stream">{renderCenter()}</main>
        <EvidencePanel />
      </div>
      <footer className="footer">
        <span>CHA-225 · KMRL Document Intelligence &amp; Action Portal</span>
        <span>AI-derived fields require human review and source traceability.</span>
      </footer>
    </div>
  );
}
