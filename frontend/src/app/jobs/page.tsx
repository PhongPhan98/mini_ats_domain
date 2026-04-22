"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";

type Job = { id: number; title: string; requirements: string; created_at?: string };
type MatchItem = { candidate_id: number; candidate_name?: string; match_score: number; explanation: string };
type MatchResponse = { job_id: number; job_title: string; results: MatchItem[] };

export default function JobsPage() {
  const [title, setTitle] = useState("");
  const [requirements, setRequirements] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [match, setMatch] = useState<MatchResponse | null>(null);
  const [loadingMatchId, setLoadingMatchId] = useState<number | null>(null);
  const { t } = useAppLanguage();

  const loadJobs = async () => {
    const data = await apiGet<Job[]>("/api/jobs");
    setJobs(data);
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const createJob = async () => {
    if (!title || !requirements) return;
    await apiPost<Job>("/api/jobs", { title, requirements });
    setTitle("");
    setRequirements("");
    await loadJobs();
  };

  const runMatch = async (jobId: number) => {
    setLoadingMatchId(jobId);
    try {
      const data = await apiPost<MatchResponse>(`/api/jobs/${jobId}/match`, {});
      setMatch(data);
    } finally {
      setLoadingMatchId(null);
    }
  };

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("jobs_title")}</h2>
        <small>{t("jobs_hint")}</small>
      </div>

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

      <div className="card">
        <h3>{t("job_list")}</h3>
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
                  <button className="btn-outline" onClick={() => runMatch(job.id)}>
                    {loadingMatchId === job.id ? t("running") : t("run_matching")}
                  </button>
                </td>
              </tr>
            ))}
            {!jobs.length && (
              <tr>
                <td colSpan={3}><small>{t("no_jobs")}</small></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {match && (
        <div className="card">
          <h3>{t("match_results")}: {match.job_title}</h3>
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
                  <td>{r.candidate_name || `#${r.candidate_id}`}</td>
                  <td>
                    <span className="chip">{r.match_score}</span>
                  </td>
                  <td>{r.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
