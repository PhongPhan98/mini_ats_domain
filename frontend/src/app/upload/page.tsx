"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { apiPatch, uploadCandidate } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import { notify } from "../../lib/toast";
import type { Candidate } from "../../components/types";

type EditableCandidate = Candidate & {
  _editing?: {
    name: string;
    email: string;
    phone: string;
    years_of_experience: string;
    skills_text: string;
    summary: string;
    linkedin_url: string;
    github_url: string;
    location: string;
    current_title: string;
    certifications_text: string;
    languages_text: string;
    projects_text: string;
  };
  _saving?: boolean;
};

function toEditing(c: Candidate) {
  return {
    name: c.name || "",
    email: c.email || "",
    phone: c.phone || "",
    years_of_experience: c.years_of_experience?.toString() || "",
    skills_text: (c.skills || []).join(", "),
    summary: c.summary || "",
    linkedin_url: c.parsed_json?.linkedin_url || "",
    github_url: c.parsed_json?.github_url || "",
    location: c.parsed_json?.location || "",
    current_title: c.parsed_json?.current_title || "",
    certifications_text: (c.parsed_json?.certifications || []).join(", "),
    languages_text: (c.parsed_json?.languages || []).join(", "),
    projects_text: (c.parsed_json?.projects || []).join(" | "),
  };
}

function confidencePill(v?: string) {
  const c = (v || "low").toLowerCase();
  return c === "high" ? "conf-high" : c === "medium" ? "conf-medium" : "conf-low";
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<EditableCandidate[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useAppLanguage();

  const totalReadiness = useMemo(() => {
    if (!results.length) return 0;
    const scoreOne = (r: EditableCandidate) => {
      let pts = 0;
      if (r.name) pts += 25;
      if (r.email) pts += 25;
      if ((r.skills || []).length >= 3) pts += 25;
      if (r.summary) pts += 25;
      return pts;
    };
    return Math.round(results.reduce((sum, x) => sum + scoreOne(x), 0) / results.length);
  }, [results]);

  const onUpload = async () => {
    if (!files.length) return;
    setLoading(true);
    setError("");

    const ok: EditableCandidate[] = [];
    let failed = 0;

    for (const f of files) {
      try {
        const data = await uploadCandidate(f);
        ok.push({ ...data, _editing: toEditing(data) });
      } catch (e: any) {
        failed += 1;
      }
    }

    setResults(ok);
    setFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (ok.length) notify(`Imported ${ok.length} CV(s)`, "success");
    if (failed) {
      setError(`${failed} file(s) failed to import.`);
      notify(`${failed} file(s) failed`, "error");
    }

    setLoading(false);
  };

  const setEditing = (id: number, key: keyof NonNullable<EditableCandidate["_editing"]>, value: string) => {
    setResults((prev) =>
      prev.map((r) =>
        r.id === id ? { ...r, _editing: { ...(r._editing || toEditing(r)), [key]: value } } : r
      )
    );
  };

  const saveCandidate = async (id: number) => {
    const item = results.find((x) => x.id === id);
    if (!item || !item._editing) return;

    setResults((prev) => prev.map((x) => (x.id === id ? { ...x, _saving: true } : x)));
    try {
      const payload = {
        name: item._editing.name || null,
        email: item._editing.email || null,
        phone: item._editing.phone || null,
        years_of_experience: item._editing.years_of_experience
          ? Number(item._editing.years_of_experience)
          : null,
        skills: item._editing.skills_text
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        summary: item._editing.summary || null,
        linkedin_url: item._editing.linkedin_url || null,
        github_url: item._editing.github_url || null,
        location: item._editing.location || null,
        current_title: item._editing.current_title || null,
        certifications: item._editing.certifications_text.split(",").map((x) => x.trim()).filter(Boolean),
        languages: item._editing.languages_text.split(",").map((x) => x.trim()).filter(Boolean),
        projects: item._editing.projects_text.split("|").map((x) => x.trim()).filter(Boolean),
      };

      const updated = await apiPatch<Candidate>(`/api/candidates/${id}`, payload);
      setResults((prev) =>
        prev.map((x) => (x.id === id ? { ...updated, _editing: toEditing(updated) } : x))
      );
      notify(t("update_success"), "success");
    } catch {
      notify(t("save_failed"), "error");
    } finally {
      setResults((prev) => prev.map((x) => (x.id === id ? { ...x, _saving: false } : x)));
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
            multiple
            accept=".pdf,.docx"
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
        </div>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <small>{files.length ? `${files.length} ${t("files_selected")}` : t("no_files_selected")}</small>
          <button style={{ width: "auto" }} onClick={onUpload} disabled={!files.length || loading}>
            {loading ? t("uploading") : `${t("upload_action")} (${files.length || 0})`}
          </button>
        </div>
        {error && <p style={{ color: "#ef4444" }}>{error}</p>}
      </div>

      {!!results.length && (
        <div className="card parsed-card">
          <div className="toolbar">
            <h3 style={{ margin: 0 }}>{t("imported_cvs")} ({results.length})</h3>
            <span className="score-pill">{t("avg_readiness")}: {totalReadiness}%</span>
          </div>
        </div>
      )}

      {results.map((r) => (
        <div className="card parsed-card" key={r.id}>
          <div className="toolbar">
            <div className="toolbar-actions">
              <strong>Candidate #{r.id}</strong>
              <Link className="chip" href={`/candidates/${r.id}`}>Review Full CV</Link>
            </div>
            <button style={{ width: "auto" }} onClick={() => saveCandidate(r.id)} disabled={r._saving}>
              {r._saving ? t("saving") : t("save_changes")}
            </button>
          </div>

          <div className="chip-wrap" style={{ marginTop: 8 }}>
            <span className={`chip ${confidencePill(r.parsed_json?.confidence?.name)}`}>name: {r.parsed_json?.confidence?.name || "low"}</span>
            <span className={`chip ${confidencePill(r.parsed_json?.confidence?.email)}`}>email: {r.parsed_json?.confidence?.email || "low"}</span>
            <span className={`chip ${confidencePill(r.parsed_json?.confidence?.phone)}`}>phone: {r.parsed_json?.confidence?.phone || "low"}</span>
            <span className={`chip ${confidencePill(r.parsed_json?.confidence?.skills)}`}>skills: {r.parsed_json?.confidence?.skills || "low"}</span>
            <span className={`chip ${confidencePill(r.parsed_json?.confidence?.projects)}`}>projects: {r.parsed_json?.confidence?.projects || "low"}</span>
          </div>

          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div className="info-tile">
              <label>{t("name")}</label>
              <input
                value={r._editing?.name || ""}
                onChange={(e) => setEditing(r.id, "name", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>{t("email")}</label>
              <input
                value={r._editing?.email || ""}
                onChange={(e) => setEditing(r.id, "email", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>{t("phone")}</label>
              <input
                value={r._editing?.phone || ""}
                onChange={(e) => setEditing(r.id, "phone", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>{t("years_experience")}</label>
              <input
                type="number"
                min={0}
                value={r._editing?.years_of_experience || ""}
                onChange={(e) => setEditing(r.id, "years_of_experience", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>Projects (separate by |)</label>
              <input
                value={r._editing?.projects_text || ""}
                onChange={(e) => setEditing(r.id, "projects_text", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div className="info-tile">
              <label>{t("skills_csv")}</label>
              <input
                value={r._editing?.skills_text || ""}
                onChange={(e) => setEditing(r.id, "skills_text", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>{t("summary")}</label>
              <textarea
                rows={3}
                value={r._editing?.summary || ""}
                onChange={(e) => setEditing(r.id, "summary", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div className="info-tile">
              <label>Current Title</label>
              <input
                value={r._editing?.current_title || ""}
                onChange={(e) => setEditing(r.id, "current_title", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>Location</label>
              <input
                value={r._editing?.location || ""}
                onChange={(e) => setEditing(r.id, "location", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>LinkedIn URL</label>
              <input
                value={r._editing?.linkedin_url || ""}
                onChange={(e) => setEditing(r.id, "linkedin_url", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>GitHub URL</label>
              <input
                value={r._editing?.github_url || ""}
                onChange={(e) => setEditing(r.id, "github_url", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>Certifications (CSV)</label>
              <input
                value={r._editing?.certifications_text || ""}
                onChange={(e) => setEditing(r.id, "certifications_text", e.target.value)}
              />
            </div>
            <div className="info-tile">
              <label>Languages (CSV)</label>
              <input
                value={r._editing?.languages_text || ""}
                onChange={(e) => setEditing(r.id, "languages_text", e.target.value)}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
