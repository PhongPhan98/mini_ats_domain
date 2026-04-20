"use client";

import { useState } from "react";
import { uploadCandidate } from "../../lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const onUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const data = await uploadCandidate(file);
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Upload CV</h2>
      <small>Supported formats: PDF, DOCX</small>
      <div style={{ marginTop: 12 }}>
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </div>
      <div style={{ marginTop: 12 }}>
        <button onClick={onUpload} disabled={!file || loading}>
          {loading ? "Uploading..." : "Upload & Parse with AI"}
        </button>
      </div>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {result && (
        <pre className="card" style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
