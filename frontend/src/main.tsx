/**
 * main.tsx — application entry point only.
 * All components live in /components and /pages.
 * Styles are imported from /styles/*.css
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/theme.css";
import "./styles/layout.css";
import "./styles/auth.css";
import "./styles/documents.css";
import "./styles/intelligence.css";
import "./styles/workflow.css";
import "./styles/comparison.css";
import "./styles/rag.css";
import "./styles/dashboard.css";
import "./styles/admin.css";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Login } from "./components/auth/Login";
import { PortalLayout } from "./components/layout/PortalLayout";

function App() {
  const { user, token, onLogin, onLogout } = useAuth();
  if (!user || !token) return <Login onLogin={onLogin} />;
  return <PortalLayout user={user} token={token} onLogout={onLogout} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
