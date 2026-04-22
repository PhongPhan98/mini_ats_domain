"use client";

import { useRef, useState } from "react";
import { uploadCandidate } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import { notify } from "../../lib/toast";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useAppLanguage();

  const onUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const data = await uploadCandidate(file);
      setResult(data);
      notify(t("update_success"), "success");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e: any) {
      const msg = e.message || t("upload_failed");
      setError(msg);
      notify(t("upload_failed"), "error");
      if (String(msg).includes("Could not extract text")) {
        notify(t("parse_warning"), "info");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>{t("upload_title")}</h2>
        <small>{t("upload_supported")}</small>
        <div style={{ marginTop: 12 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <div style={{ marginTop: 12 }}>
          <button onClick={onUpload} disabled={!file || loading}>
            {loading ? t("uploading") : t("upload_action")}
          </button>
        </div>
        {error && <p style={{ color: "#ef4444" }}>{error}</p>}
      </div>

      {result && (
        <div className="card">
          <h3>{t("parsed_candidate")}</h3>
          <div className="grid grid-2">
            <div>
              <small>Name</small>
              <p>{result.name || "-"}</p>
            </div>
            <div>
              <small>Email</small>
              <p>{result.email || "-"}</p>
            </div>
          </div>

          <small>Skills</small>
          <div className="chip-wrap" style={{ marginTop: 8 }}>
            {(result.skills || []).map((s: string) => (
              <span key={s} className="chip">
                {s}
              </span>
            ))}
          </div>

          <details style={{ marginTop: 12 }}>
            <summary>{t("raw_json")}</summary>
            <pre className="card" style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
