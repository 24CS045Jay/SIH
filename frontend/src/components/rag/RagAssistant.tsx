import { useState } from "react";
import { RAGResponse } from "../../types";
import { API, authHeaders } from "../../api/client";

const RECENT_KEY = "kmrl_rag_recent";
const MAX_RECENT = 5;

function getRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveRecent(q: string) {
  const existing = getRecent().filter((r) => r !== q);
  localStorage.setItem(RECENT_KEY, JSON.stringify([q, ...existing].slice(0, MAX_RECENT)));
}

interface RagAssistantProps {
  token: string;
}

export function RagAssistant({ token }: RagAssistantProps) {
  const [question, setQuestion] = useState(
    "What changed in the brake inspection frequency, who is affected, and what action is required?"
  );
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<string[]>(getRecent);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await fetch(`${API}/search/ask`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail ?? "Search failed");
      setResponse(data);
      saveRecent(question);
      setRecent(getRecent());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rag-assistant">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 3 — Source-grounded search</p>
          <h2>Ask the approved documents</h2>
          <p className="muted">
            Answers are limited to access-controlled chunks from approved document versions.
          </p>
        </div>
      </div>
      <form className="rag-form" onSubmit={ask}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about approved documents"
          aria-label="Question"
        />
        <button className="primary-button" disabled={busy || question.trim().length < 3}>
          {busy ? "Retrieving evidence…" : "Ask assistant"}
        </button>
      </form>
      <div className="rag-demo-prompts">
        <button
          className="text-button"
          onClick={() =>
            setQuestion(
              "What changed in the brake inspection frequency, who is affected, and what action is required?"
            )
          }
        >
          Demo: brake inspection change
        </button>
        <button
          className="text-button"
          onClick={() => setQuestion("What is the approved cafeteria menu for next Tuesday?")}
        >
          Demo: deliberately unanswerable
        </button>
      </div>
      {recent.length > 0 && (
        <div className="rag-recent-searches">
          <strong>Recent:</strong>
          {recent.map((r) => (
            <button key={r} onClick={() => setQuestion(r)} title={r}>
              {r.length > 50 ? r.slice(0, 50) + "…" : r}
            </button>
          ))}
        </div>
      )}
      {error && <p className="form-error">{error}</p>}
      {response && (
        <div className="rag-result">
          <div className={response.refusal ? "rag-answer refusal" : "rag-answer"}>
            <p className="eyebrow">
              {response.refusal ? "Guardrail response" : "AI-generated answer"}
            </p>
            <p>{response.answer}</p>
            <strong>{response.disclaimer}</strong>
          </div>
          {!response.refusal && (
            <aside className="citation-panel">
              <h3>Citations</h3>
              {response.citations.map((citation) => (
                <div className="citation-card" key={citation.citation_id}>
                  <strong>
                    [{citation.citation_id}] {citation.document_title}
                  </strong>
                  <span>Page {citation.page_no}</span>
                  <p>{citation.quote}</p>
                  <a
                    href={`${API}/documents/${citation.document_id}/source`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open original
                  </a>
                </div>
              ))}
            </aside>
          )}
        </div>
      )}
    </section>
  );
}
