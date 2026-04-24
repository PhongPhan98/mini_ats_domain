"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { parseCandidatePreview, uploadCandidateReviewed } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import { notify } from "../../lib/toast";

type Draft = {
  file: File;
  filename: string;
  data: any;
  editing: {
    name: string;
    email: string;
    phone: string;
    years_of_experience: string;
    skills_text: string;
    summary: string;
    current_title: string;
    location: string;
    linkedin_url: string;
    github_url: string;
    certifications_text: string;
    languages_text: string;
    projects_text: string;
  };
  saving?: boolean;
  savedCandidateId?: number;
};

function fromParsed(file: File, parsed: any): Draft {
  return {
    file,
    filename: file.name,
    data: parsed,
    editing: {
      name: parsed?.name || "",
      email: parsed?.email || "",
      phone: parsed?.phone || "",
      years_of_experience: parsed?.years_of_experience?.toString?.() || "",
      skills_text: (parsed?.skills || []).join(", "),
      summary: parsed?.summary || "",
      current_title: parsed?.current_title || "",
      location: parsed?.location || "",
      linkedin_url: parsed?.linkedin_url || "",
      github_url: parsed?.github_url || "",
      certifications_text: (parsed?.certifications || []).join(", "),
      languages_text: (parsed?.languages || []).join(", "),
      projects_text: (parsed?.projects || []).join(" | "),
    },
  };
}

function confidenceClass(v?: string) {
  const c = (v || "low").toLowerCase();
  return c === "high" ? "conf-high" : c === "medium" ? "conf-medium" : "conf-low";
}
function isLow(v?: string, current?: string) {
  return (v || "low").toLowerCase() === "low" && !(current || "").trim();
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [bulkSaving, setBulkSaving] = useState(false);
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useAppLanguage();

  const current = drafts[idx];
  const parseWarning = String(current?.data?.parse_warning || "");
  const scannedSuspected = Boolean(current?.data?.scanned_suspected);
  const aiStatus = String(current?.data?.ai_parse_status || "rule_only");
  const aiProvider = String(current?.data?.ai_provider || "local");
  const [cvPreviewUrl, setCvPreviewUrl] = useState("");

  useEffect(() => {
    if (!current?.file) {
      setCvPreviewUrl("");
      return;
    }
    const nextUrl = URL.createObjectURL(current.file);
    setCvPreviewUrl(nextUrl);
    return () => {
      URL.revokeObjectURL(nextUrl);
    };
  }, [current?.file]);

  const score = useMemo(() => {
    if (!current?.data) return 0;
    let pts = 0;
    if (current.editing.name) pts += 20;
    if (current.editing.email) pts += 20;
    if (current.editing.phone) pts += 10;
    if (current.editing.skills_text) pts += 20;
    if (current.editing.summary) pts += 20;
    if (current.editing.current_title) pts += 10;
    return pts;
  }, [current]);

  const onParseOnly = async () => {
    if (!files.length) return;
    setLoading(true);
    setError("");
    const next: Draft[] = [];
    let failed = 0;

    for (const f of files) {
      try {
        const res = await parseCandidatePreview(f);
        next.push(fromParsed(f, res.parsed));
      } catch {
        failed += 1;
      }
    }

    setDrafts(next);
    setIdx(0);
    setFiles([]);
    if (inputRef.current) inputRef.current.value = "";
    if (next.length) notify(`Parsed ${next.length} CV(s). Review before import.`, "success");
    if (failed) {
      setError(`${failed} file(s) failed to parse.`);
      notify(`${failed} file(s) failed to parse`, "error");
    }
    setLoading(false);
  };

  const update = (k: keyof Draft["editing"], v: string) => {
    setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, editing: { ...d.editing, [k]: v } } : d)));
  };

  const removeCurrent = () => {
    setDrafts((prev) => {
      const arr = prev.filter((_, i) => i !== idx);
      const nextIdx = Math.min(idx, Math.max(0, arr.length - 1));
      setIdx(nextIdx);
      return arr;
    });
  };


  const buildEditedPayload = (d: Draft) => ({
    name: d.editing.name || null,
    email: d.editing.email || null,
    phone: d.editing.phone || null,
    years_of_experience: d.editing.years_of_experience ? Number(d.editing.years_of_experience) : null,
    skills: d.editing.skills_text.split(",").map((x) => x.trim()).filter(Boolean),
    summary: d.editing.summary || null,
    current_title: d.editing.current_title || null,
    location: d.editing.location || null,
    linkedin_url: d.editing.linkedin_url || null,
    github_url: d.editing.github_url || null,
    certifications: d.editing.certifications_text.split(",").map((x) => x.trim()).filter(Boolean),
    languages: d.editing.languages_text.split(",").map((x) => x.trim()).filter(Boolean),
    projects: d.editing.projects_text.split("|").map((x) => x.trim()).filter(Boolean),
  });

  const saveCurrent = async () => {
    if (!current) return;
    setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, saving: true } : d)));
    try {
      const saved = await uploadCandidateReviewed(current.file, buildEditedPayload(current));
      setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, saving: false, savedCandidateId: saved.id } : d)));
      notify("Imported after review successfully", "success");
    } catch (e: any) {
      setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, saving: false } : d)));
      notify(t("save_failed"), "error");
    }
  };

  const saveAllReviewed = async () => {
    const pending = drafts.map((d, i) => ({ d, i })).filter(({ d }) => !d.savedCandidateId);
    if (!pending.length) return;

    setBulkSaving(true);
    let ok = 0;
    let fail = 0;

    for (const { d, i } of pending) {
      setDrafts((prev) => prev.map((x, idx) => (idx === i ? { ...x, saving: true } : x)));
      try {
        const saved = await uploadCandidateReviewed(d.file, buildEditedPayload(d));
        ok += 1;
        setDrafts((prev) => prev.map((x, idx) => (idx === i ? { ...x, saving: false, savedCandidateId: saved.id } : x)));
      } catch {
        fail += 1;
        setDrafts((prev) => prev.map((x, idx) => (idx === i ? { ...x, saving: false } : x)));
      }
    }

    setBulkSaving(false);
    if (ok) notify(`Imported ${ok} CV(s)`, "success");
    if (fail) notify(`${fail} CV(s) failed`, "error");
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>{t("upload_title")}</h2>
        <small>{t("upload_supported")} — parse only first, then review and save to import.</small>
        <div style={{ marginTop: 12 }}>
          <input ref={inputRef} type="file" multiple accept=".pdf,.docx" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
        </div>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <small>{files.length ? `${files.length} ${t("files_selected")}` : t("no_files_selected")}</small>
          <button style={{ width: "auto" }} onClick={onParseOnly} disabled={!files.length || loading}>
            {loading ? t("uploading") : "Parse with AI (Review First)"}
          </button>
        </div>
        {error && <p style={{ color: "#ef4444" }}>{error}</p>}
      </div>

      {!!drafts.length && current && (
        <div className="card split-review">
          <div className="toolbar">
            <div className="toolbar-actions">
              <button className="btn-outline" style={{ width: "auto" }} onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx <= 0}>↑ Prev</button>
              <button className="btn-outline" style={{ width: "auto" }} onClick={saveAllReviewed} disabled={bulkSaving}>{bulkSaving ? "Importing..." : "Save & Import All Reviewed"}</button>
              <button className="btn-outline" style={{ width: "auto" }} onClick={() => setIdx((i) => Math.min(drafts.length - 1, i + 1))} disabled={idx >= drafts.length - 1}>↓ Next</button>
              <span className="chip">{idx + 1}/{drafts.length}</span>
              <span className="score-pill">Readiness: {score}%</span>
            </div>
            <div className="toolbar-actions">
              <button className="btn-outline" style={{ width: "auto" }} onClick={removeCurrent}>Delete Draft</button>
              <button style={{ width: "auto" }} onClick={saveCurrent} disabled={!!current.savedCandidateId || current.saving}>{current.saving ? t("saving") : current.savedCandidateId ? "Imported" : "Save & Import"}</button>
            </div>
          </div>

          <div className="split-grid" style={{ marginTop: 12 }}>
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>Original CV</h3>
              <small>{current.filename}</small>
              <div style={{ marginTop: 10 }}>
                <iframe
                  title={current.filename}
                  src={cvPreviewUrl}
                  style={{ width: "100%", height: 700, border: "1px solid var(--border)", borderRadius: 10 }}
                />
              </div>
              {current.savedCandidateId ? (
                <div style={{ marginTop: 10 }}>
                  <Link className="chip" href={`/candidates/${current.savedCandidateId}`}>Open Candidate Profile</Link>
                </div>
              ) : null}
            </div>

            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>HR Review Form</h3>
              <small className="low-hint">Red fields are low-confidence and still empty.</small>
              <div className="chip-wrap" style={{ marginTop: 8 }}>
                <span className="chip">AI Provider: {aiProvider}</span>
                <span className="chip">AI Status: {aiStatus}</span>
              </div>



              {(parseWarning || scannedSuspected) ? (
                <div className="card" style={{ marginTop: 10, borderColor: "#f59e0b", background: "rgba(245,158,11,0.08)" }}>
                  <strong>Parsing warning</strong>
                  <div style={{ marginTop: 4 }}>
                    {parseWarning || "This CV looks scanned/image-based. Lightweight mode may not extract full text."}
                  </div>
                  <small style={{ display: "block", marginTop: 6 }}>
                    Recommended: upload DOCX/text-based PDF, or continue with manual HR review fields below.
                  </small>
                </div>
              ) : null}

              <div className="chip-wrap" style={{ marginTop: 8 }}>
                <span className={`chip ${confidenceClass(current.data?.confidence?.name)}`}>name: {current.data?.confidence?.name || "low"}</span>
                <span className={`chip ${confidenceClass(current.data?.confidence?.email)}`}>email: {current.data?.confidence?.email || "low"}</span>
                <span className={`chip ${confidenceClass(current.data?.confidence?.phone)}`}>phone: {current.data?.confidence?.phone || "low"}</span>
                <span className={`chip ${confidenceClass(current.data?.confidence?.skills)}`}>skills: {current.data?.confidence?.skills || "low"}</span>
                <span className={`chip ${confidenceClass(current.data?.confidence?.projects)}`}>projects: {current.data?.confidence?.projects || "low"}</span>
              </div>

              <div className="grid grid-2" style={{ marginTop: 10 }}>
                <div><label>{t("name")}</label><input className={isLow(current.data?.confidence?.name, current.editing.name) ? "field-low" : ""} value={current.editing.name} onChange={(e) => update("name", e.target.value)} /></div>
                <div><label>{t("email")}</label><input className={isLow(current.data?.confidence?.email, current.editing.email) ? "field-low" : ""} value={current.editing.email} onChange={(e) => update("email", e.target.value)} /></div>
                <div><label>{t("phone")}</label><input className={isLow(current.data?.confidence?.phone, current.editing.phone) ? "field-low" : ""} value={current.editing.phone} onChange={(e) => update("phone", e.target.value)} /></div>
                <div><label>{t("years_experience")}</label><input type="number" min={0} value={current.editing.years_of_experience} onChange={(e) => update("years_of_experience", e.target.value)} /></div>
                <div><label>Current Title</label><input value={current.editing.current_title} onChange={(e) => update("current_title", e.target.value)} /></div>
                <div><label>Location</label><input value={current.editing.location} onChange={(e) => update("location", e.target.value)} /></div>
                <div><label>LinkedIn</label><input value={current.editing.linkedin_url} onChange={(e) => update("linkedin_url", e.target.value)} /></div>
                <div><label>GitHub</label><input value={current.editing.github_url} onChange={(e) => update("github_url", e.target.value)} /></div>
              </div>

              <div className="grid" style={{ marginTop: 10 }}>
                <div><label>{t("skills_csv")}</label><input className={isLow(current.data?.confidence?.skills, current.editing.skills_text) ? "field-low" : ""} value={current.editing.skills_text} onChange={(e) => update("skills_text", e.target.value)} /></div>
                <div><label>Certifications (CSV)</label><input value={current.editing.certifications_text} onChange={(e) => update("certifications_text", e.target.value)} /></div>
                <div><label>Languages (CSV)</label><input value={current.editing.languages_text} onChange={(e) => update("languages_text", e.target.value)} /></div>
                <div><label>Projects (separate by |)</label><input className={isLow(current.data?.confidence?.projects, current.editing.projects_text) ? "field-low" : ""} value={current.editing.projects_text} onChange={(e) => update("projects_text", e.target.value)} /></div>
                <div><label>{t("summary")}</label><textarea className={isLow(current.data?.confidence?.summary, current.editing.summary) ? "field-low" : ""} rows={5} value={current.editing.summary} onChange={(e) => update("summary", e.target.value)} /></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
