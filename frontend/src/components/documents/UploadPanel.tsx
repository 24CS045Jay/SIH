import { useState } from "react";
import { allowedExt } from "../../types";
import { API, authHeaders } from "../../api/client";

interface UploadPanelProps {
  token: string;
  onUploaded: () => void;
}

export function UploadPanel({ token, onUploaded }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [language, setLanguage] = useState<"english" | "malayalam">("english");

  function validate(next: File | null) {
    setFile(next);
    setError("");
    setMessage("");
    if (!next) return;
    const ext = `.${next.name.split(".").pop()?.toLowerCase()}`;
    if (!allowedExt.includes(ext))
      setError("Rejected: unsupported extension. Use PDF, image, or text files.");
    else if (next.size > 25 * 1024 * 1024)
      setError("Rejected: file exceeds the 25 MB limit.");
    else
      setMessage(`Validation passed: ${next.name} · ${(next.size / 1024).toFixed(1)} KB`);
  }

  async function upload() {
    if (!file || error) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("language", language);
      const response = await fetch(`${API}/documents/upload`, {
        method: "POST",
        headers: authHeaders(token),
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Upload rejected");
      setMessage(`Accepted: ${data.message} Status: ${data.status}.`);
      setFile(null);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="upload-panel">
      <div
        className="upload-dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          validate(e.dataTransfer.files[0] ?? null);
        }}
      >
        <strong>Drop a document here</strong>
        <span>or</span>
        <label className="secondary-button">
          Choose file
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt,.md,.csv"
            onChange={(e) => validate(e.target.files?.[0] ?? null)}
          />
        </label>
        <small>PDF, images, and text · maximum 25 MB · duplicate hashes are rejected</small>
      </div>

      {/* Bilingual OCR toggle — experimental */}
      <div className="ocr-lang-toggle">
        <label htmlFor="ocr-language">OCR language:</label>
        <select
          id="ocr-language"
          value={language}
          onChange={(e) => setLanguage(e.target.value as "english" | "malayalam")}
        >
          <option value="english">English</option>
          <option value="malayalam">Malayalam</option>
        </select>
        {language === "malayalam" && (
          <span className="experimental-badge">⚠ EXPERIMENTAL — not yet benchmarked</span>
        )}
      </div>

      {message && <p className="success-message">{message}</p>}
      {error && <p className="form-error">{error}</p>}
      <button
        className="primary-button"
        disabled={!file || !!error || busy}
        onClick={upload}
      >
        {busy ? "Uploading…" : "Upload and queue OCR"}
      </button>
    </section>
  );
}
