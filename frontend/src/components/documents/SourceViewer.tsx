import { useState } from "react";
import { Detail } from "../../types";
import { API } from "../../api/client";

interface SourceViewerProps {
  detail: Detail;
  token: string;
  onClose: () => void;
}

export function SourceViewer({ detail, token, onClose }: SourceViewerProps) {
  const [page, setPage] = useState(0);
  const current = detail.pages[page];

  return (
    <section className="source-viewer">
      <div className="viewer-heading">
        <div>
          <p className="eyebrow">Source evidence</p>
          <h3>{detail.document.title}</h3>
          <p className="muted">
            Version {detail.document.version_label} · {detail.document.status}
          </p>
        </div>
        <button className="secondary-button" onClick={onClose}>
          Close source
        </button>
      </div>
      <div className="viewer-grid">
        <div className="source-frame">
          <iframe
            title="Original uploaded source"
            src={`${API}/documents/${detail.document.id}/source`}
          />
        </div>
        <div className="ocr-panel">
          <div className="page-controls">
            <button
              className="secondary-button"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </button>
            <strong>
              Page {current?.page_no ?? 0} / {detail.pages.length}
            </strong>
            <button
              className="secondary-button"
              disabled={page >= detail.pages.length - 1}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
          {current && (
            <>
              <div className={current.low_confidence ? "confidence-badge low" : "confidence-badge"}>
                {current.low_confidence
                  ? "Low OCR confidence — needs review"
                  : "OCR confidence acceptable"}{" "}
                · {Math.round((current.ocr_confidence ?? 0) * 100)}%
              </div>
              <pre className="ocr-text">
                {current.ocr_text || "No OCR text extracted for this page."}
              </pre>
            </>
          )}
        </div>
      </div>
      <div className="synthetic-watermark viewer-watermark">
        SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA.
      </div>
    </section>
  );
}
