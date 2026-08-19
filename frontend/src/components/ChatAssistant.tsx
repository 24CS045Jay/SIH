import { useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Citation = { citation_id: string; document_title: string; page_no: number; quote: string; document_id: string };
type ChatResponse = { answer: string; refusal: boolean; disclaimer: string; citations: Citation[] };

function RailBot() {
  return <div className="railbot" aria-hidden="true"><span className="railbot-antenna" /><div className="railbot-face"><i /><i /><b /></div><span className="railbot-wheel wheel-left" /><span className="railbot-wheel wheel-right" /></div>;
}

export default function ChatAssistant({ token }: { token: string }) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const prompts = [
    "What changed in brake inspection frequency?",
    "Who is affected by the new maintenance checklist?",
    "What deadline is stated in the safety circular?",
    "What is the approved cafeteria menu for next Tuesday?",
  ];
  async function ask(event?: React.FormEvent) {
    event?.preventDefault();
    const next = question.trim();
    if (next.length < 3 || busy) return;
    setBusy(true); setError("");
    try {
      const result = await fetch(`${API}/search/ask`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ question: next }) });
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail ?? "The assistant could not complete this request.");
      setResponse(data);
    } catch (err) { setError(err instanceof Error ? err.message : "The assistant could not complete this request."); }
    finally { setBusy(false); }
  }
  return <section className="chat-assistant"><div className="chat-hero"><div><span className="chat-kicker">KMRL / SOURCE-GROUNDED ASSISTANT</span><h2>Ask the evidence.</h2><p>RailBot searches approved, access-controlled document chunks. It will not guess when the corpus does not support an answer.</p></div><div className="chat-hero-badge"><RailBot /><span>R-01<br /><b>ONLINE</b></span></div></div><div className="chat-stage"><div className="chat-transcript" aria-live="polite">{!response && !busy && <div className="chat-empty"><RailBot /><h3>How can I help you today?</h3><p>Ask about a document, date, department, asset, obligation, or change.</p></div>}{busy && <div className="chat-loading"><RailBot /><div><strong>Reading approved evidence</strong><span className="typing-dots"><i /><i /><i /></span></div></div>}{response && <><div className="chat-question"><span>You asked</span><p>{question}</p></div><div className={`chat-answer-bubble ${response.refusal ? "is-refusal" : ""}`}><div className="chat-answer-head"><RailBot /><span>{response.refusal ? "Evidence boundary" : "RailBot answer"}</span></div><p className="chat-answer-copy">{response.answer}</p><small>{response.disclaimer}</small></div>{!response.refusal && <div className="chat-sources"><div className="chat-section-label">Supporting sources <b>{response.citations.length}</b></div>{response.citations.map((citation) => <article className="chat-source-card" key={citation.citation_id}><div className="source-index">{citation.citation_id}</div><div><strong>{citation.document_title}</strong><span>Page {citation.page_no}</span><p>{citation.quote}</p><a href={`${API}/documents/${citation.document_id}/source`} target="_blank" rel="noreferrer">Open original →</a></div></article>)}</div>}</>}</div><div className="chat-prompts"><div className="chat-section-label">Try a focused question</div>{prompts.map((prompt, index) => <button className={`prompt-chip prompt-${index}`} key={prompt} onClick={() => { setQuestion(prompt); setResponse(null); }}>{prompt}</button>)}</div><form className="chat-composer" onSubmit={ask}><textarea aria-label="Question for the document assistant" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about the approved documents…" rows={2} /><button className="chat-send" type="submit" disabled={busy || question.trim().length < 3} aria-label="Ask assistant">{busy ? "…" : "→"}</button></form>{error && <p className="form-error" role="alert">{error}</p>}</div><div className="chat-disclaimer">AI-generated answer — verify against the cited source. Unrelated questions return an evidence-bound refusal.</div></section>;
}
