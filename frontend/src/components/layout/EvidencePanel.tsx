export function EvidencePanel() {
  return (
    <aside className="evidence-panel" aria-label="Trust layer evidence">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Trust layer</p>
          <h2>Evidence</h2>
        </div>
        <span className="status-dot">Awaiting selection</span>
      </div>
      <div className="evidence-empty">
        <strong>Select an item to inspect evidence</strong>
        <p>
          Source document, page citation, confidence, and reviewer state will be shown here.
        </p>
      </div>
      <div className="synthetic-watermark">
        SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA.
      </div>
    </aside>
  );
}
