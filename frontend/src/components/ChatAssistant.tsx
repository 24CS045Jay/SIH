import { useState } from "react";
import { apiFetch, apiUrl, authHeaders } from "../api/client";

type Citation = { citation_id: string; document_title: string; page_no: number; section_number?: string | null; section_title?: string | null; quote: string; document_id: string; version_id: string };
type ChatResponse = { answer: string; refusal: boolean; disclaimer: string; citations: Citation[]; scope?: string; refusal_reason?: string | null; diagnostics?: { candidate_count?: number; latency_ms?: number } };

type Props = { token: string; currentDocumentId?: string; currentDocumentTitle?: string };

function RailBot() {
  return <div className="railbot" aria-hidden="true"><span className="railbot-signal" /><span className="railbot-core">R1</span><span className="railbot-label">EVIDENCE LINK</span></div>;
}

export default function ChatAssistant({ token, currentDocumentId, currentDocumentTitle }: Props) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [scope, setScope] = useState<"all" | "document">(currentDocumentId ? "document" : "all");
  const prompts = [
    "What changed in brake inspection frequency?",
    "Who is affected by the new maintenance checklist?",
    "What deadline is stated in the safety circular?",
    "What is the approved cafeteria menu for next Tuesday?",
  ];
  const effectiveScope = scope === "document" && currentDocumentId ? "document" : "all";

  async function ask(event?: React.FormEvent) {
    event?.preventDefault();
    const next = question.trim();
    if (next.length < 3 || busy) return;
    setBusy(true); setError("");
    try {
      const body: { question: string; scope: string; document_id?: string } = { question: next, scope: effectiveScope };
      if (effectiveScope === "document" && currentDocumentId) body.document_id = currentDocumentId;
      const data = await apiFetch<ChatResponse>("/search/ask", { method: "POST", headers: { ...authHeaders(token), "Content-Type": "application/json" }, body: JSON.stringify(body) }, 30000);
      setResponse(data);
    } catch (err) { setError(err instanceof Error ? err.message : "The assistant could not complete this request."); }
    finally { setBusy(false); }
  }

  return <section className="chat-assistant">
    <div className="chat-hero"><div><span className="chat-kicker">KMRL / SOURCE-GROUNDED ASSISTANT</span><h2>Ask the evidence.</h2><p>RailBot searches only approved, access-controlled evidence. It will not guess when the selected scope does not support an answer.</p></div><div className="chat-hero-badge"><RailBot /><span>R-01<br /><b>ONLINE</b></span></div></div>
    <div className="chat-scope-bar" aria-label="Document search scope"><div><strong>Search scope</strong><span>{effectiveScope === "document" ? currentDocumentTitle ?? "Current document" : "All approved documents"}</span></div><label>Scope<select value={scope} onChange={(event) => { setScope(event.target.value as "all" | "document"); setResponse(null); }}><option value="all">All approved documents</option><option value="document" disabled={!currentDocumentId}>Current document{currentDocumentTitle ? ` — ${currentDocumentTitle}` : ""}</option></select></label></div>
    <div className="chat-stage"><div className="chat-transcript" aria-live="polite">
      {!response && !busy && <div className="chat-empty"><RailBot /><h3>How can I help you today?</h3><p>Ask about a document, date, department, asset, obligation, or change.</p></div>}
      {busy && <div className="chat-loading"><RailBot /><div><strong>Reading approved evidence</strong><span className="typing-dots"><i /><i /><i /></span></div></div>}
      {response && <><div className="chat-question"><span>You asked · {response.scope === "document" ? "current document" : "all approved documents"}</span><p>{question}</p></div><div className={`chat-answer-bubble ${response.refusal ? "is-refusal" : ""}`}><div className="chat-answer-head"><RailBot /><span>{response.refusal ? "Evidence boundary" : "RailBot answer"}</span></div><p className="chat-answer-copy">{response.answer}</p><small>{response.disclaimer}</small>{response.refusal && response.refusal_reason && <em className="chat-refusal-reason">Reason: evidence did not meet the relevance or scope threshold.</em>}</div>{!response.refusal && <div className="chat-sources"><div className="chat-section-label">Supporting sources <b>{response.citations.length}</b></div>{response.citations.map((citation) => <article className="chat-source-card" key={citation.citation_id}><div className="source-index">{citation.citation_id}</div><div><strong>{citation.document_title}</strong><span>Page {citation.page_no}{citation.section_title ? ` · ${citation.section_title}` : ""}</span><p>{citation.quote}</p><small>Version {citation.version_id.slice(0, 8)}…</small><a href={`${apiUrl(`/documents/${citation.document_id}/source`)}`} target="_blank" rel="noreferrer">Open original →</a></div></article>)}</div>}</>}
    </div><div className="chat-prompts"><div className="chat-section-label">Try a focused question</div>{prompts.map((prompt, index) => <button className={`prompt-chip prompt-${index}`} key={prompt} onClick={() => { setQuestion(prompt); setResponse(null); }}>{prompt}</button>)}</div><form className="chat-composer" onSubmit={ask}><textarea aria-label="Question for the document assistant" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about the approved documents…" rows={2} /><button className="chat-send" type="submit" disabled={busy || question.trim().length < 3} aria-label="Ask assistant">{busy ? "…" : "→"}</button></form>{error && <p className="form-error" role="alert">{error}</p>}</div><div className="chat-disclaimer">AI-generated answer — verify against the cited source. Unrelated questions return an evidence-bound refusal.</div>
  </section>;
}
