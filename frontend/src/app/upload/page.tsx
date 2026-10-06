"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { parseCandidatePreview, uploadCandidateReviewed } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import { notify } from "../../lib/toast";
import RichTextField from "../../components/RichTextField";

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
    portfolio_urls_text: string;
    certifications_text: string;
    languages_text: string;
    projects_text: string;
    education_text: string;
    previous_companies_text: string;
    experience_text: string;
    domain_tags_text: string;
    achievements_text: string;
    preferred_location: string;
    notice_period: string;
  };
  saving?: boolean;
  savedCandidateId?: number;
};

function fromParsed(file: File, parsed: any, sourceText = ""): Draft {
  return {
    file,
    filename: file.name,
    data: { ...parsed, source_text: sourceText },
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
      portfolio_urls_text: (parsed?.portfolio_urls || []).join(", "),
      certifications_text: (parsed?.certifications || []).join(", "),
      languages_text: (parsed?.languages || []).join(", "),
      projects_text: (parsed?.projects || []).join(" | "),
      education_text: (parsed?.education || []).join("\n"),
      previous_companies_text: (parsed?.previous_companies || []).join(", "),
      experience_text: (parsed?.experience_details || []).join("\n"),
      domain_tags_text: (parsed?.domain_tags || []).join(", "),
      achievements_text: (parsed?.achievements || []).join("\n"),
      preferred_location: parsed?.preferred_location || "",
      notice_period: parsed?.notice_period || "",
    },
  };
}

function isDocx(filename: string) {
  return filename.toLowerCase().endsWith(".docx");
}

const MAX_FILE_SIZE = 20 * 1024 * 1024;

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function confidenceClass(v?: string) {
  const c = (v || "low").toLowerCase();
  return c === "high"
    ? "conf-high"
    : c === "medium"
      ? "conf-medium"
      : "conf-low";
}
function isLow(v?: string, current?: string) {
  return (v || "low").toLowerCase() === "low" && !(current || "").trim();
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [parseProgress, setParseProgress] = useState({ done: 0, total: 0 });
  const [bulkSaving, setBulkSaving] = useState(false);
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useAppLanguage();

  const current = drafts[idx];
  const parseWarning = String(current?.data?.parse_warning || "");
  const scannedSuspected = Boolean(current?.data?.scanned_suspected);
  const [cvPreviewUrl, setCvPreviewUrl] = useState("");
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [activeField, setActiveField] = useState<string>("");

  const addFiles = (incoming: File[]) => {
    const valid: File[] = [];
    const rejected: string[] = [];
    for (const file of incoming) {
      const ext = file.name.toLowerCase().split(".").pop();
      if (ext !== "pdf" && ext !== "docx") rejected.push(`${file.name}: unsupported format`);
      else if (file.size > MAX_FILE_SIZE) rejected.push(`${file.name}: larger than 20 MB`);
      else if (!file.size) rejected.push(`${file.name}: empty file`);
      else valid.push(file);
    }
    setFiles((previous) => {
      const unique = new Map(previous.map((file) => [`${file.name}-${file.size}-${file.lastModified}`, file]));
      valid.forEach((file) => unique.set(`${file.name}-${file.size}-${file.lastModified}`, file));
      return Array.from(unique.values());
    });
    if (rejected.length) {
      const message = rejected.slice(0, 3).join("; ");
      setError(message);
      notify(message, "error");
    } else setError("");
  };

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
    if (current.editing.education_text) pts += 10;
    if (current.editing.experience_text) pts += 10;
    return Math.min(100, pts);
  }, [current]);

  const onParseOnly = async () => {
    if (!files.length) return;
    setStep(2);
    setLoading(true);
    setError("");
    setParseProgress({ done: 0, total: files.length });
    const results: Array<Draft | null> = new Array(files.length).fill(null);
    let cursor = 0;
    const worker = async () => {
      while (cursor < files.length) {
        const currentIndex = cursor++;
        const file = files[currentIndex];
        try {
          const res = await parseCandidatePreview(file);
          results[currentIndex] = fromParsed(file, res.parsed, res.source_text);
        } catch {
          results[currentIndex] = null;
        } finally {
          setParseProgress((progress) => ({ ...progress, done: progress.done + 1 }));
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(3, files.length) }, worker));
    const next = results.filter((draft): draft is Draft => draft !== null);
    const failed = results.length - next.length;

    setDrafts(next);
    if (next.length) setStep(3);
    setIdx(0);
    setFiles([]);
    if (inputRef.current) inputRef.current.value = "";
    if (next.length)
      notify(`Parsed ${next.length} CV(s). Review before import.`, "success");
    if (failed) {
      setError(`${failed} file(s) failed to parse.`);
      notify(`${failed} file(s) failed to parse`, "error");
    }
    setLoading(false);
  };

  const update = (k: keyof Draft["editing"], v: string) => {
    setDrafts((prev) =>
      prev.map((d, i) =>
        i === idx ? { ...d, editing: { ...d.editing, [k]: v } } : d,
      ),
    );
  };

  const updateRich = (field: "summary" | "education" | "experience_details" | "achievements", editingKey: keyof Draft["editing"], plainText: string, html: string) => {
    setDrafts((previous) => previous.map((draft, draftIndex) => draftIndex === idx ? {
      ...draft,
      editing: { ...draft.editing, [editingKey]: plainText },
      data: { ...draft.data, rich_text: { ...(draft.data?.rich_text || {}), [field]: html } },
    } : draft));
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
    confidence: d.data?.confidence || {},
    confidence_score: d.data?.confidence_score ?? null,
    completeness_score: d.data?.completeness_score ?? null,
    missing_critical_fields: d.data?.missing_critical_fields || [],
    review_recommended: Boolean(d.data?.review_recommended),
    field_sources: d.data?.field_sources || {},
    field_evidence: d.data?.field_evidence || {},
    experience_months: d.data?.experience_months ?? null,
    experience_calculation: d.data?.experience_calculation || null,
    parser_version: d.data?.parser_version || "3.0",
    source: d.data?.source || "reviewed_preview",
    parse_warning: d.data?.parse_warning || null,
    rich_text: d.data?.rich_text || {},
    scanned_suspected: Boolean(d.data?.scanned_suspected),
    name: d.editing.name || null,
    email: d.editing.email || null,
    phone: d.editing.phone || null,
    years_of_experience: d.editing.years_of_experience
      ? Number(d.editing.years_of_experience)
      : null,
    skills: d.editing.skills_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    summary: d.editing.summary || null,
    current_title: d.editing.current_title || null,
    location: d.editing.location || null,
    linkedin_url: d.editing.linkedin_url || null,
    github_url: d.editing.github_url || null,
    portfolio_urls: d.editing.portfolio_urls_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    certifications: d.editing.certifications_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    languages: d.editing.languages_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    projects: d.editing.projects_text
      .split("|")
      .map((x) => x.trim())
      .filter(Boolean),
    education: d.editing.education_text
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean),
    previous_companies: d.editing.previous_companies_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    experience_details: d.editing.experience_text
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean),
    domain_tags: d.editing.domain_tags_text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean),
    achievements: d.editing.achievements_text
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean),
    preferred_location: d.editing.preferred_location || null,
    notice_period: d.editing.notice_period || null,
    experience_timeline: d.data?.experience_timeline || [],
  });

  const saveCurrent = async () => {
    if (!current) return;
    setDrafts((prev) =>
      prev.map((d, i) => (i === idx ? { ...d, saving: true } : d)),
    );
    try {
      const saved = await uploadCandidateReviewed(
        current.file,
        buildEditedPayload(current),
      );
      setStep(4);
      setDrafts((prev) =>
        prev.map((d, i) =>
          i === idx ? { ...d, saving: false, savedCandidateId: saved.id } : d,
        ),
      );
      notify("Imported after review successfully", "success");
    } catch (e: any) {
      setDrafts((prev) =>
        prev.map((d, i) => (i === idx ? { ...d, saving: false } : d)),
      );
      notify(t("save_failed"), "error");
    }
  };

  const saveAllReviewed = async () => {
    const pending = drafts
      .map((d, i) => ({ d, i }))
      .filter(({ d }) => !d.savedCandidateId);
    if (!pending.length) return;

    setBulkSaving(true);
    let ok = 0;
    let fail = 0;
    let cursor = 0;
    const worker = async () => {
      while (cursor < pending.length) {
        const { d, i } = pending[cursor++];
        setDrafts((prev) => prev.map((x, idx) => idx === i ? { ...x, saving: true } : x));
        try {
          const saved = await uploadCandidateReviewed(d.file, buildEditedPayload(d));
          ok += 1;
          setDrafts((prev) => prev.map((x, idx) => idx === i ? { ...x, saving: false, savedCandidateId: saved.id } : x));
        } catch {
          fail += 1;
          setDrafts((prev) => prev.map((x, idx) => idx === i ? { ...x, saving: false } : x));
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(3, pending.length) }, worker));

    setBulkSaving(false);
    if (ok) notify(`Imported ${ok} CV(s)`, "success");
    if (fail) notify(`${fail} CV(s) failed`, "error");
  };

  return (
    <div className="grid">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Candidate intake</span>
          <h1>{t("upload_title")}</h1>
          <p>Add several resumes at once. Candidate details are extracted so you only review what needs attention.</p>
        </div>
        <Link className="btn-secondary" href="/candidates">View candidates</Link>
      </div>

      <div className="card upload-card">
        <div className="upload-steps" aria-label="Import progress">
          {["Choose files", "Extract details", "Review", "Import"].map((label, index) => (
            <div key={label} className={`upload-step ${step >= index + 1 ? "step-on" : ""}`}>
              <span>{index + 1}</span><strong>{label}</strong>
            </div>
          ))}
        </div>
        <small>
          {t("upload_supported")} — parse only first, then review and save to
          import.
        </small>
        <div
          className={`drop-zone ${dragActive ? "drop-zone-active" : ""}`}
          onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => { event.preventDefault(); setDragActive(false); }}
          onDrop={(event) => { event.preventDefault(); setDragActive(false); addFiles(Array.from(event.dataTransfer.files)); }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") inputRef.current?.click(); }}
        >
          <div className="drop-zone-icon" aria-hidden="true">+</div>
          <h2>Drop CVs here</h2>
          <p>or click to choose files from your computer</p>
          <span>PDF or DOCX, up to 20 MB each</span>
          <input
            className="visually-hidden"
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx"
            onChange={(e) => addFiles(Array.from(e.target.files || []))}
          />
        </div>
        {!!files.length && (
          <div className="upload-queue">
            <div className="toolbar">
              <div><strong>{files.length} CV{files.length === 1 ? "" : "s"} ready</strong><small>Duplicates are removed automatically.</small></div>
              <button className="text-button" type="button" onClick={() => { setFiles([]); setError(""); }}>Clear all</button>
            </div>
            <div className="file-list">
              {files.map((file, fileIndex) => (
                <div className="file-row" key={`${file.name}-${file.size}-${file.lastModified}`}>
                  <span className="file-type">{isDocx(file.name) ? "DOCX" : "PDF"}</span>
                  <span className="file-name"><strong>{file.name}</strong><small>{formatBytes(file.size)}</small></span>
                  <button type="button" className="file-remove" aria-label={`Remove ${file.name}`} onClick={() => setFiles((items) => items.filter((_, index) => index !== fileIndex))}>Remove</button>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="upload-action-bar">
          <small>{files.length ? "Your files stay in review until you choose to import them." : t("no_files_selected")}</small>
          <button
            className="btn-large"
            onClick={onParseOnly}
            disabled={!files.length || loading}
          >
            {loading ? `Reading CVs (${parseProgress.done}/${parseProgress.total})` : `Extract candidate details${files.length ? ` from ${files.length} CV${files.length === 1 ? "" : "s"}` : ""}`}
          </button>
        </div>
        {error && <div className="inline-alert" role="alert">{error}</div>}
      </div>

      {loading ? (
        <div className="card processing-overlay">
          <div className="spinner" />
          <div><strong>Extracting candidate details</strong><small>{parseProgress.done} of {parseProgress.total} complete. You can review each result before importing.</small></div>
          <div className="progress-track"><span style={{ width: `${parseProgress.total ? (parseProgress.done / parseProgress.total) * 100 : 0}%` }} /></div>
        </div>
      ) : null}

      {!!drafts.length && current && (
        <div className="card split-review">
          <div className="toolbar">
            <div className="toolbar-actions">
              <button
                className="btn-outline"
                style={{ width: "auto" }}
                onClick={() => setIdx((i) => Math.max(0, i - 1))}
                disabled={idx <= 0}
              >
                ↑ Prev
              </button>
              <button
                className="btn-outline"
                style={{ width: "auto" }}
                onClick={saveAllReviewed}
                disabled={bulkSaving}
              >
                {bulkSaving ? "Importing..." : "Save & Import All Reviewed"}
              </button>
              <button
                className="btn-outline"
                style={{ width: "auto" }}
                onClick={() =>
                  setIdx((i) => Math.min(drafts.length - 1, i + 1))
                }
                disabled={idx >= drafts.length - 1}
              >
                ↓ Next
              </button>
              <span className="chip">
                {idx + 1}/{drafts.length}
              </span>
              <span className="score-pill">Readiness: {score}%</span>
            </div>
            <div className="toolbar-actions">
              <button
                className="btn-outline"
                style={{ width: "auto" }}
                onClick={removeCurrent}
              >
                Delete Draft
              </button>
              <button
                style={{ width: "auto" }}
                onClick={saveCurrent}
                disabled={!!current.savedCandidateId || current.saving}
              >
                {current.saving
                  ? t("saving")
                  : current.savedCandidateId
                    ? "Imported"
                    : "Save & Import"}
              </button>
            </div>
          </div>

          <div className="split-grid" style={{ marginTop: 12 }}>
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>Original CV</h3>
              <small>Field mapping focus: {activeField || "none"}</small>
              <small>{current.filename}</small>
              <div style={{ marginTop: 10 }}>
                {isDocx(current.filename) ? (
                  <div className="cv-text-preview">
                    {current.data?.source_text ||
                      "No readable text was found in this DOCX. Use Download original to inspect it manually."}
                  </div>
                ) : (
                  <iframe
                    title={current.filename}
                    src={cvPreviewUrl}
                    style={{
                      width: "100%",
                      height: 700,
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                    }}
                  />
                )}
                <a
                  className="cv-download"
                  href={cvPreviewUrl}
                  download={current.filename}
                >
                  Download original
                </a>
              </div>
              {current.savedCandidateId ? (
                <div style={{ marginTop: 10 }}>
                  <Link
                    className="chip"
                    href={`/candidates/${current.savedCandidateId}`}
                  >
                    Open Candidate Profile
                  </Link>
                </div>
              ) : null}
            </div>

            <div className="card" style={{ marginBottom: 0 }}>
              <h3 style={{ marginTop: 0 }}>HR Review Form</h3>
              <small className="low-hint">
                Red fields are low-confidence and still empty.
              </small>
              <div className="chip-wrap" style={{ marginTop: 8 }}>
                <span className="chip">Local CV extraction</span>
                <span className="chip">
                  Profile completeness: {current.data?.completeness_score ?? 0}%
                </span>
                <span className="chip">
                  Parser v{current.data?.parser_version || "3.0"}
                </span>
              </div>

              {parseWarning || scannedSuspected ? (
                <div
                  className="card"
                  style={{
                    marginTop: 10,
                    borderColor: "#f59e0b",
                    background: "rgba(245,158,11,0.08)",
                  }}
                >
                  <strong>Parsing warning</strong>
                  <div style={{ marginTop: 4 }}>
                    {parseWarning ||
                      "This CV looks scanned/image-based. Lightweight mode may not extract full text."}
                  </div>
                  <small style={{ display: "block", marginTop: 6 }}>
                    Recommended: upload DOCX/text-based PDF, or continue with
                    manual HR review fields below.
                  </small>
                </div>
              ) : null}

              <div className="chip-wrap" style={{ marginTop: 8 }}>
                <span
                  className={`chip ${confidenceClass(current.data?.confidence?.name)}`}
                >
                  name: {current.data?.confidence?.name || "low"}
                </span>
                <span
                  className={`chip ${confidenceClass(current.data?.confidence?.email)}`}
                >
                  email: {current.data?.confidence?.email || "low"}
                </span>
                <span
                  className={`chip ${confidenceClass(current.data?.confidence?.phone)}`}
                >
                  phone: {current.data?.confidence?.phone || "low"}
                </span>
                <span
                  className={`chip ${confidenceClass(current.data?.confidence?.skills)}`}
                >
                  skills: {current.data?.confidence?.skills || "low"}
                </span>
                <span
                  className={`chip ${confidenceClass(current.data?.confidence?.projects)}`}
                >
                  projects: {current.data?.confidence?.projects || "low"}
                </span>
              </div>

              <div className="grid grid-2" style={{ marginTop: 10 }}>
                <div>
                  <label>{t("name")}</label>
                  <input
                    className={
                      isLow(
                        current.data?.confidence?.name,
                        current.editing.name,
                      )
                        ? "field-low"
                        : ""
                    }
                    value={current.editing.name}
                    onChange={(e) => update("name", e.target.value)}
                  />
                </div>
                <div>
                  <label>{t("email")}</label>
                  <input
                    className={
                      isLow(
                        current.data?.confidence?.email,
                        current.editing.email,
                      )
                        ? "field-low"
                        : ""
                    }
                    value={current.editing.email}
                    onChange={(e) => update("email", e.target.value)}
                  />
                </div>
                <div>
                  <label>{t("phone")}</label>
                  <input
                    className={
                      isLow(
                        current.data?.confidence?.phone,
                        current.editing.phone,
                      )
                        ? "field-low"
                        : ""
                    }
                    value={current.editing.phone}
                    onChange={(e) => update("phone", e.target.value)}
                  />
                </div>
                <div>
                  <label>{t("years_experience")}</label>
                  <input
                    type="number"
                    min={0}
                    value={current.editing.years_of_experience}
                    onChange={(e) =>
                      update("years_of_experience", e.target.value)
                    }
                  />
                </div>
                <div>
                  <label>Current Title</label>
                  <input
                    value={current.editing.current_title}
                    onChange={(e) => update("current_title", e.target.value)}
                  />
                </div>
                <div>
                  <label>Location</label>
                  <input
                    value={current.editing.location}
                    onChange={(e) => update("location", e.target.value)}
                  />
                </div>
                <div>
                  <label>LinkedIn</label>
                  <input
                    value={current.editing.linkedin_url}
                    onChange={(e) => update("linkedin_url", e.target.value)}
                  />
                </div>
                <div>
                  <label>GitHub</label>
                  <input
                    value={current.editing.github_url}
                    onChange={(e) => update("github_url", e.target.value)}
                  />
                </div>
                <div className="grid-column-full">
                  <label>Portfolio websites (comma-separated)</label>
                  <input
                    value={current.editing.portfolio_urls_text}
                    onChange={(e) =>
                      update("portfolio_urls_text", e.target.value)
                    }
                    placeholder="https://portfolio.example.com"
                  />
                </div>
              </div>

              <div className="grid" style={{ marginTop: 10 }}>
                <div>
                  <label>{t("skills_csv")}</label>
                  <input
                    className={
                      isLow(
                        current.data?.confidence?.skills,
                        current.editing.skills_text,
                      )
                        ? "field-low"
                        : ""
                    }
                    value={current.editing.skills_text}
                    onChange={(e) => update("skills_text", e.target.value)}
                  />
                </div>
                <div>
                  <label>Certifications (CSV)</label>
                  <input
                    value={current.editing.certifications_text}
                    onChange={(e) =>
                      update("certifications_text", e.target.value)
                    }
                  />
                </div>
                <div>
                  <label>Languages (CSV)</label>
                  <input
                    value={current.editing.languages_text}
                    onChange={(e) => update("languages_text", e.target.value)}
                  />
                </div>
                <div>
                  <label>Projects (separate by |)</label>
                  <input
                    className={
                      isLow(
                        current.data?.confidence?.projects,
                        current.editing.projects_text,
                      )
                        ? "field-low"
                        : ""
                    }
                    value={current.editing.projects_text}
                    onChange={(e) => update("projects_text", e.target.value)}
                  />
                </div>
                <RichTextField
                  label={t("summary")}
                  value={current.editing.summary}
                  html={current.data?.rich_text?.summary}
                  className={isLow(current.data?.confidence?.summary, current.editing.summary) ? "field-low" : ""}
                  onSave={(plain, html) => updateRich("summary", "summary", plain, html)}
                />

                <RichTextField
                  label="Education details"
                  value={current.editing.education_text}
                  html={current.data?.rich_text?.education}
                  listMode
                  onSave={(plain, html) => updateRich("education", "education_text", plain, html)}
                />
                <div>
                  <label>Previous companies (CSV)</label>
                  <input
                    value={current.editing.previous_companies_text}
                    onChange={(e) =>
                      update("previous_companies_text", e.target.value)
                    }
                  />
                </div>
                <RichTextField
                  label="Experience details"
                  value={current.editing.experience_text}
                  html={current.data?.rich_text?.experience_details}
                  listMode
                  onSave={(plain, html) => updateRich("experience_details", "experience_text", plain, html)}
                />
                <RichTextField
                  label="Achievements"
                  value={current.editing.achievements_text}
                  html={current.data?.rich_text?.achievements}
                  listMode
                  onSave={(plain, html) => updateRich("achievements", "achievements_text", plain, html)}
                />
                <div>
                  <label>Domain tags (CSV)</label>
                  <input
                    value={current.editing.domain_tags_text}
                    onChange={(e) => update("domain_tags_text", e.target.value)}
                  />
                </div>
                <small>Preferences and availability are filled only when stated in the CV. Confirm these with the candidate if blank.</small>
                <div className="grid grid-2">
                  <div>
                    <label>Preferred location</label>
                    <input
                      placeholder="Not stated in CV"
                      value={current.editing.preferred_location}
                      onChange={(e) =>
                        update("preferred_location", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <label>Notice period</label>
                    <input
                      placeholder="Not stated in CV"
                      value={current.editing.notice_period}
                      onChange={(e) => update("notice_period", e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
