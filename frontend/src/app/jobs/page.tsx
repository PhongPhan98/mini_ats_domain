"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";

type Job = { id: number; title: string; requirements: string };
type MatchItem = { candidate_id: number; candidate_name?: string; match_score: number; explanation: string };

type MatchResponse = { job_id: number; job_title: string; results: MatchItem[] };

export default function JobsPage() {
  const [title, setTitle] = useState("");
  const [requirements, setRequirements] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [match, setMatch] = useState<MatchResponse | null>(null);

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
    const data = await apiPost<MatchResponse>(`/api/jobs/${jobId}/match`, {});
    setMatch(data);
  };

  return (
    <div className="grid">
      <div className="card">
        <h2>Create Job</h2>
        <div className="grid" style={{ marginTop: 8 }}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Job title" />
          <textarea
            style={{ minHeight: 120 }}
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            placeholder="Enter requirements"
          />
          <button onClick={createJob}>Save Job</button>
        </div>
      </div>

      <div className="card">
        <h2>Jobs</h2>
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.title}</td>
                <td>
                  <button className="btn-outline" onClick={() => runMatch(job.id)}>
                    Run Matching
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {match && (
        <div className="card">
          <h2>Match Results: {match.job_title}</h2>
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Score</th>
                <th>Explanation</th>
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
