import { Repository } from "../components/documents/Repository";

interface Module2PageProps {
  token: string;
  role: string;
}

/** Module 2 — Document Intake & Processing: upload, OCR, processing status. */
export function Module2Page({ token, role }: Module2PageProps) {
  return (
    <div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Module 2</p>
          <h2>Document Intake &amp; Processing</h2>
          <p className="muted">
            Upload documents, monitor OCR processing, and review extracted text with
            confidence indicators.
          </p>
        </div>
      </div>
      <Repository token={token} role={role} browseOnly={false} />
    </div>
  );
}
