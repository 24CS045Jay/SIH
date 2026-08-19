import { useState } from "react";
import { Repository } from "../components/documents/Repository";
import { RagAssistant } from "../components/rag/RagAssistant";

interface Module3PageProps {
  token: string;
  role: string;
}

type M3View = "browse" | "ask";

/**
 * Module 3 — Document Network & Intelligence
 * Combines document browse/search (browse-only, no upload) with RAG Q&A.
 */
export function Module3Page({ token, role }: Module3PageProps) {
  const [view, setView] = useState<M3View>("browse");

  return (
    <div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 3</p>
          <h2>Document Network &amp; Intelligence</h2>
          <p className="muted">
            Search and browse approved documents, or ask the AI assistant questions grounded
            in source evidence.
          </p>
        </div>
      </div>

      {/* Sub-navigation: Browse & Search | Ask a Question */}
      <div className="module-tabs" role="tablist" style={{ marginBottom: 24 }}>
        <button
          className={`module-tab ${view === "browse" ? "active" : ""}`}
          onClick={() => setView("browse")}
          role="tab"
          aria-selected={view === "browse"}
        >
          Browse &amp; Search
        </button>
        <button
          className={`module-tab ${view === "ask" ? "active" : ""}`}
          onClick={() => setView("ask")}
          role="tab"
          aria-selected={view === "ask"}
        >
          Ask a Question
        </button>
      </div>

      {view === "browse" && (
        <Repository token={token} role={role} browseOnly={true} />
      )}
      {view === "ask" && (
        <RagAssistant token={token} />
      )}
    </div>
  );
}
