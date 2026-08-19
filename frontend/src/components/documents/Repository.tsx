import { useEffect, useState } from "react";
import { Doc, Detail } from "../../types";
import { API, authHeaders } from "../../api/client";
import { UploadPanel } from "./UploadPanel";
import { SourceViewer } from "./SourceViewer";
import { IntelligenceCard } from "../intelligence/IntelligenceCard";

interface RepositoryProps {
  token: string;
  role: string;
  /** When true, upload panel is hidden (Module 3 browse-only mode) */
  browseOnly?: boolean;
}

export function Repository({ token, role, browseOnly = false }: RepositoryProps) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [intelligenceDoc, setIntelligenceDoc] = useState<Doc | null>(null);
  const [refresh, setRefresh] = useState(0);

  async function load() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    const response = await fetch(`${API}/documents?${params}`, {
      headers: authHeaders(token),
    });
    if (response.ok) setDocs(await response.json());
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, search, status]);

  async function openSource(doc: Doc) {
    const response = await fetch(`${API}/documents/${doc.id}`, {
      headers: authHeaders(token),
    });
    if (response.ok) setDetail(await response.json());
  }

  if (intelligenceDoc) {
    return (
      <IntelligenceCard
        token={token}
        documentId={intelligenceDoc.id}
        role={role}
        onViewSource={async () => {
          const response = await fetch(`${API}/documents/${intelligenceDoc.id}`, {
            headers: authHeaders(token),
          });
          if (response.ok) {
            setDetail(await response.json());
            setIntelligenceDoc(null);
          }
        }}
      />
    );
  }

  if (detail) {
    return (
      <SourceViewer detail={detail} token={token} onClose={() => setDetail(null)} />
    );
  }

  return (
    <div className="repository">
      {!browseOnly && (
        <UploadPanel token={token} onUploaded={() => setRefresh((v) => v + 1)} />
      )}
      <div className="repository-heading">
        <div>
          <p className="eyebrow">Document repository</p>
          <h3>Uploaded sources</h3>
        </div>
        <div className="filter-row">
          <input
            placeholder="Search title"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="review_ready">Review ready</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>
      {docs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">DOC</div>
          <h3>No documents found</h3>
          <p>Upload a synthetic PDF, image, or text file to begin the OCR pipeline.</p>
        </div>
      ) : (
        <div className="document-table">
          {docs.map((doc) => (
            <div className="document-row" key={doc.id}>
              <div>
                <strong>{doc.title}</strong>
                <span>
                  {doc.type.toUpperCase()} · {doc.version_label} · owner {doc.owner_name}
                </span>
              </div>
              <span className={`status-badge ${doc.status}`}>
                {doc.status.replace("_", " ")}
              </span>
              <span className="classification-cell">{doc.classification}</span>
              <button
                className="secondary-button"
                onClick={() => setIntelligenceDoc(doc)}
              >
                Intelligence
              </button>
              <button className="secondary-button" onClick={() => openSource(doc)}>
                Open source
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
