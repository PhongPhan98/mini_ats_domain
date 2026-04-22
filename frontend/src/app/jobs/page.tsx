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
  const { t } = useAppLanguage();

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
      const data = await apiPost<MatchResponse>(`/api/jobs/${jobId}/match?threshold=${threshold}`, {});
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

  const softDelete = async (id: number) => {
    await apiDelete(`/api/jobs/${id}`);
    await loadJobs();
    notify("Moved to Trash", "success");
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
                <td>
                  {editingId === job.id ? (
                    <div className="grid" style={{ gap: 6 }}>
                      <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                      <textarea rows={3} value={editReq} onChange={(e) => setEditReq(e.target.value)} />
                    </div>
                  ) : (
                    job.title
                  )}
                </td>
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
                    {!showTrash && editingId === job.id && (
                      <>
                        <button onClick={saveEdit}>Save</button>
                        <button className="btn-outline" onClick={() => setEditingId(null)}>Cancel</button>
                      </>
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
                    </div>
                  </td>
                  <td>
                    <span className="chip">{r.match_score}</span>
                  </td>
                  <td>{r.explanation}</td>
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
