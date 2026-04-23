"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import { notify } from "../../lib/toast";

type Job = { id: number; title: string; requirements: string; created_at?: string };
type MatchItem = { candidate_id: number; candidate_name?: string; match_score: number; explanation: string };
type MatchResponse = { job_id: number; job_title: string; results: MatchItem[] };

export default function JobsPage() {
  const [title, setTitle] = useState("");
  const [requirements, setRequirements] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [match, setMatch] = useState<MatchResponse | null>(null);
  const [loadingMatchId, setLoadingMatchId] = useState<number | null>(null);
  const [showTrash, setShowTrash] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editReq, setEditReq] = useState("");
  const [thresholdByJob, setThresholdByJob] = useState<Record<number, number>>({});
  const [modalFullscreen, setModalFullscreen] = useState(false);
  const { t, lang } = useAppLanguage();

  const loadJobs = async () => {
    const data = await apiGet<Job[]>(`/api/jobs?include_deleted=${showTrash ? "true" : "false"}`);
    setJobs(data);

    const next: Record<number, number> = {};
    await Promise.all(data.map(async (j) => {
      try {
        const cfg = await apiGet<{ job_id: number; threshold: number }>(`/api/jobs/${j.id}/settings`);
        next[j.id] = cfg.threshold;
      } catch {
        next[j.id] = 50;
      }
    }));
    setThresholdByJob(next);
  };

  useEffect(() => {
    loadJobs();
  }, [showTrash]);

  const createJob = async () => {
    if (!title || !requirements) return;
    await apiPost<Job>("/api/jobs", { title, requirements });
    setTitle("");
    setRequirements("");
    await loadJobs();
    notify("Job created", "success");
  };

  const runMatch = async (jobId: number) => {
    setLoadingMatchId(jobId);
    try {
      const threshold = thresholdByJob[jobId] ?? 50;
      const data = await apiPost<MatchResponse>(`/api/jobs/${jobId}/match?threshold=${threshold}&lang=${lang}`, {});
      setMatch(data);
    } finally {
      setLoadingMatchId(null);
    }
  };

  const startEdit = (job: Job) => {
    setEditingId(job.id);
    setEditTitle(job.title);
    setEditReq(job.requirements);
  };

  const saveEdit = async () => {
    if (!editingId) return;
    await apiPatch(`/api/jobs/${editingId}`, { title: editTitle, requirements: editReq });
    setEditingId(null);
    await loadJobs();
    notify("Job updated", "success");
  };

  const saveThreshold = async (id: number) => {
    const threshold = Math.max(0, Math.min(100, Number(thresholdByJob[id] ?? 50)));
    await apiPatch(`/api/jobs/${id}/settings`, { threshold });
    setThresholdByJob((prev) => ({ ...prev, [id]: threshold }));
    notify("Threshold updated", "success");
  };


  const appendReqTemplate = (type: "must" | "nice" | "responsibility") => {
    const head = type === "must" ? "Must-have:" : type === "nice" ? "Nice-to-have:" : "Responsibilities:";
    const block = `\n${head}\n- `;
    setEditReq((prev) => (prev || "") + block);
  };

  const formatExplanation = (text: string) => {
    let out = text || "";
    if (lang === "vi") {
      out = out
        .replace("Overall match score", "Điểm phù hợp tổng thể")
        .replace("Skills fit contributes strongly", "Mức độ phù hợp kỹ năng đóng góp chính")
        .replace("Experience check", "Đánh giá kinh nghiệm")
        .replace("requirement is", "yêu cầu là")
        .replace("year(s)", "năm")
        .replace("Context relevance", "Mức độ liên quan ngữ cảnh")
        .replace("Main gaps", "Khoảng trống chính")
        .replace("no major required-skill gaps detected", "không có khoảng trống kỹ năng bắt buộc đáng kể")
        .replace("none explicitly required", "không có kỹ năng bắt buộc cụ thể");
    }
    return out.replace(/\.\s+/g, ".\n");
  };

  const softDelete = async (id: number) => {
    await apiDelete(`/api/jobs/${id}`);
    await loadJobs();
    notify("Moved to Trash", "success");
  };

  const shortlistFromMatch = async (candidateId: number) => {
    await apiPatch(`/api/candidates/${candidateId}`, { status: "screening" });
    notify("Candidate moved to screening", "success");
  };

  const restore = async (id: number) => {
    await apiPost(`/api/jobs/${id}/restore`, {});
    await loadJobs();
    notify("Job restored", "success");
  };

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <h2 style={{ marginTop: 0 }}>{t("jobs_title")}</h2>
            <small>{t("jobs_hint")}</small>
          </div>
          <button className="btn-outline" style={{ width: "auto" }} onClick={() => setShowTrash((v) => !v)}>
            {showTrash ? "Back to Active" : "Trash"}
          </button>
        </div>
      </div>

      {!showTrash && (
        <div className="card">
          <h3>{t("create_job")}</h3>
          <div className="grid" style={{ marginTop: 8 }}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("job_title")} />
            <textarea
              style={{ minHeight: 120 }}
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder={t("enter_requirements")}
            />
            <button onClick={createJob}>{t("save_job")}</button>
          </div>
        </div>
      )}

      <div className="card">
        <h3>{showTrash ? "Job Trash" : t("job_list")}</h3>
        <table>
          <thead>
            <tr>
              <th>{t("job_title")}</th>
              <th>{t("created")}</th>
              <th>{t("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.title}</td>
                <td>{job.created_at ? new Date(job.created_at).toLocaleString() : "-"}</td>
                <td>
                  <div className="toolbar-actions">
                    {!showTrash && editingId !== job.id && (
                      <>
                        <input
                          type="number"
                          min={0}
                          max={100}
                          value={thresholdByJob[job.id] ?? 50}
                          onChange={(e) => setThresholdByJob((prev) => ({ ...prev, [job.id]: Number(e.target.value || 0) }))}
                          style={{ width: 90 }}
                        />
                        <button className="btn-outline" onClick={() => saveThreshold(job.id)}>Save %</button>
                        <button className="btn-outline" onClick={() => runMatch(job.id)}>
                          {loadingMatchId === job.id ? t("running") : `${t("run_matching")} (≥${thresholdByJob[job.id] ?? 50}%)`}
                        </button>
                      </>
                    )}
                    {!showTrash && editingId !== job.id && (
                      <button className="btn-outline" onClick={() => startEdit(job)}>Edit</button>
                    )}
                    {!showTrash ? (
                      <button className="btn-outline" onClick={() => softDelete(job.id)}>Delete</button>
                    ) : (
                      <button className="btn-outline" onClick={() => restore(job.id)}>Restore</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!jobs.length && (
              <tr>
                <td colSpan={3}><small>{showTrash ? "Trash is empty." : t("no_jobs")}</small></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>


      {editingId !== null && (
        <div className="modal-overlay" onClick={() => setEditingId(null)}>
          <div className={`modal-card ${modalFullscreen ? "modal-full" : ""}`} onClick={(e) => e.stopPropagation()}>
            <div className="toolbar">
              <h3 style={{ margin: 0 }}>Edit Job</h3>
              <div className="toolbar-actions">
                <button className="btn-outline" style={{ width: "auto" }} onClick={() => setModalFullscreen((v) => !v)}>{modalFullscreen ? "Window" : "Fullscreen"}</button>
                <button className="btn-outline" style={{ width: "auto" }} onClick={() => setEditingId(null)}>×</button>
              </div>
            </div>
            <div className="grid" style={{ marginTop: 10 }}>
              <div>
                <label>{t("job_title")}</label>
                <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
              </div>
              <div>
                <label>Requirements</label>
                <div className="toolbar-actions" style={{ marginBottom: 8 }}>
                  <button type="button" className="btn-outline" style={{ width: "auto" }} onClick={() => appendReqTemplate("must")}>+ Must-have</button>
                  <button type="button" className="btn-outline" style={{ width: "auto" }} onClick={() => appendReqTemplate("nice")}>+ Nice-to-have</button>
                  <button type="button" className="btn-outline" style={{ width: "auto" }} onClick={() => appendReqTemplate("responsibility")}>+ Responsibilities</button>
                </div>
                <textarea rows={12} value={editReq} onChange={(e) => setEditReq(e.target.value)} />
              </div>
              <div className="toolbar-actions" style={{ justifyContent: "flex-end" }}>
                <button className="btn-outline" style={{ width: "auto" }} onClick={() => setEditingId(null)}>Cancel</button>
                <button style={{ width: "auto" }} onClick={saveEdit}>Save</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {match && (
        <div className="card">
          <h3>{t("match_results")}: {match.job_title}</h3>
          <small>Only candidates with matching score above selected threshold are shown.</small>
          <table>
            <thead>
              <tr>
                <th>{t("candidate")}</th>
                <th>{t("score")}</th>
                <th>{t("explanation")}</th>
              </tr>
            </thead>
            <tbody>
              {match.results.map((r) => (
                <tr key={r.candidate_id}>
                  <td>
                    <div className="toolbar-actions">
                      <span>{r.candidate_name || `#${r.candidate_id}`}</span>
                      <Link className="chip" href={`/candidates/${r.candidate_id}`}>View</Link>
                      <button className="btn-outline" style={{ width: "auto" }} onClick={() => shortlistFromMatch(r.candidate_id)}>Shortlist</button>
                    </div>
                  </td>
                  <td>
                    <span className="chip">{r.match_score}</span>
                  </td>
                  <td><div className="explain-box">{formatExplanation(r.explanation)}</div></td>
                </tr>
              ))}
              {!match.results.length && (
                <tr><td colSpan={3}><small>No candidates above 50% match.</small></td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
