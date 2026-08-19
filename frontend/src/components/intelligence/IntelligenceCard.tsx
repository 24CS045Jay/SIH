import { useEffect, useState } from "react";
import { IntelligenceCardData, IntelligenceField } from "../../types";
import { API, authHeaders } from "../../api/client";
import { REVIEWER_ROLES } from "../../types";

interface IntelligenceCardProps {
  token: string;
  documentId: string;
  role: string;
  onViewSource: (page?: number) => void;
}

export function IntelligenceCard({ token, documentId, role, onViewSource }: IntelligenceCardProps) {
  const [card, setCard] = useState<IntelligenceCardData | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    fetch(`${API}/documents/${documentId}/intelligence`, {
      headers: authHeaders(token),
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Intelligence is still processing");
        setCard(data);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Intelligence unavailable"));
  }, [documentId, token]);

  if (error)
    return (
      <section className="intelligence-card">
        <p className="eyebrow">AI intelligence</p>
        <h3>Processing intelligence</h3>
        <p className="muted">{error}. Refresh after OCR and intelligence processing complete.</p>
      </section>
    );

  if (!card)
    return (
      <section className="intelligence-card">
        <p className="eyebrow">AI intelligence</p>
        <h3>Loading Intelligence Card…</h3>
      </section>
    );

  async function save(field: IntelligenceField) {
    const response = await fetch(`${API}/documents/${documentId}/intelligence/corrections`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ field: field.field, correction: draft, reason: "other" }),
    });
    const data = await response.json();
    if (!response.ok) {
      setSaved(data.detail ?? "Correction rejected");
      return;
    }
    setCard((current) => (current ? { ...current, [field.field]: data } : current));
    setEditing(null);
    setSaved("Correction logged in feedback.");
  }

  function renderField(label: string, field: IntelligenceField) {
    return (
      <div className="intelligence-field" key={field.prediction_id}>
        <div className="field-label">
          <strong>{label}</strong>
          <span className="confidence-badge">
            {field.source} · {Math.round(field.confidence * 100)}%
          </span>
        </div>
        {editing === field.field ? (
          <div className="edit-row">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label={`Edit ${label}`}
            />
            <button className="primary-button" onClick={() => save(field)}>
              Save correction
            </button>
          </div>
        ) : (
          <div className="field-value">
            <span>{field.value}</span>
            <div className="field-actions">
              <button
                className="text-button"
                onClick={() => onViewSource(field.source_span?.page_no)}
              >
                View source{field.source_span ? ` · p.${field.source_span.page_no}` : ""}
              </button>
              <button
                className="text-button"
                disabled={!REVIEWER_ROLES.has(role)}
                onClick={() => {
                  setEditing(field.field);
                  setDraft(field.value);
                }}
              >
                Edit
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <section className="intelligence-card">
      <div className="repository-heading">
        <div>
          <p className="eyebrow">AI-generated · human-reviewable</p>
          <h3>Intelligence Card</h3>
          <p className="muted">
            {card.title}. Every field retains confidence, provenance, and a correction path.
          </p>
        </div>
      </div>
      {saved && <p className="success-message">{saved}</p>}
      <div className="intelligence-section">
        <h4>Classification and summary</h4>
        {renderField("Document type", card.classification)}
        {renderField("Executive summary", card.summary)}
      </div>
      <div className="intelligence-section">
        <h4>Key facts and entities</h4>
        {card.key_facts.map((f) => renderField("Key fact", f))}
        {card.entities.map((f) => renderField(f.field.replace("entity:", "Entity: "), f))}
      </div>
      <div className="intelligence-section">
        <h4>Actions, deadline, priority, and routing</h4>
        {card.actions.map((f) => renderField("Proposed action", f))}
        {renderField("Deadline", card.deadline)}
        {renderField("Priority + reason codes", card.priority)}
        {renderField("Suggested department", card.routing)}
      </div>
    </section>
  );
}
