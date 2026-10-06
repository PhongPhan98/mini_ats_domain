"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import PipelineColumn from "../../components/PipelineColumn";
import { apiGet, updateCandidateStage } from "../../lib/api";
import { notify } from "../../lib/toast";
import { CANDIDATE_STATUSES, formatCandidateStatus } from "../../lib/candidates";
import type { Candidate, CandidateStatus } from "../../components/types";

type JobLite = { id: number; title: string; department?: string; location?: string };
const VISIBLE_STEP = 30;
const normalizeSearch = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();

export default function PipelinePage() {
  const [dragKey, setDragKey] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [jobSearch, setJobSearch] = useState("");
  const [overStage, setOverStage] = useState<CandidateStatus | null>(null);
  const [selectedJobId, setSelectedJobId] = useState(0);
  const [visibleByStage, setVisibleByStage] = useState<Record<string, number>>({});
  const qc = useQueryClient();
  const jobsQuery = useQuery({ queryKey: ["pipeline-jobs"], queryFn: () => apiGet<JobLite[]>("/api/jobs") });
  const jobs = jobsQuery.data || [];
  const boardQuery = useQuery({
    queryKey: ["pipeline-candidates", selectedJobId],
    queryFn: () => apiGet<Candidate[]>(`/api/candidates/pipeline${selectedJobId ? `?job_id=${selectedJobId}` : ""}`),
  });
  const candidates = boardQuery.data || [];
  const filteredJobs = jobs.filter((job) => job.id === selectedJobId || normalizeSearch(`${job.title} ${job.department || ""} ${job.location || ""}`).includes(normalizeSearch(jobSearch.trim())));
  const selectedJob = jobs.find((job) => job.id === selectedJobId);
  const filtered = useMemo(() => {
    const terms = normalizeSearch(keyword.trim()).split(/\s+/).filter(Boolean);
    return candidates.filter((candidate) => {
      const text = normalizeSearch(`${candidate.name || ""} ${candidate.email || ""} ${(candidate.skills || []).join(" ")} ${candidate.parsed_json?.current_title || ""} ${candidate.job_title || ""}`);
      return terms.every((term) => text.includes(term));
    });
  }, [candidates, keyword]);
  const byStage = useMemo(() => Object.fromEntries(CANDIDATE_STATUSES.map((stage) => [stage, filtered.filter((candidate) => (candidate.status || "applied") === stage)])) as Record<CandidateStatus, Candidate[]>, [filtered]);
  useEffect(() => { setVisibleByStage({}); setDragKey(null); setOverStage(null); }, [selectedJobId, keyword]);

  const mutation = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: Candidate; stage: CandidateStatus }) => updateCandidateStage(candidate.id, stage, candidate.application_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline-candidates"] }),
  });
  const moveToStage = async (key: string, stage: CandidateStatus) => {
    const candidate = candidates.find((item) => item.board_key === key);
    if (!candidate || candidate.status === stage || mutation.isPending || !candidate.can_move) return;
    try {
      await mutation.mutateAsync({ candidate, stage });
      notify(`${candidate.name || "Candidate"} moved to ${formatCandidateStatus(stage)}`, "success");
    } catch {
      notify("Could not move this card. Refresh the board and check your access.", "error");
    } finally { setDragKey(null); setOverStage(null); }
  };

  return (
    <div className="grid page-enter">
      <div className="page-heading">
        <div><span className="eyebrow">Hiring workspace</span><h1>Candidate pipeline</h1><p>Move each application forward and keep every hiring decision in view.</p></div>
        <div className="toolbar-actions"><Link className="btn-secondary" href="/jobs">Manage jobs</Link><Link className="btn-secondary nav-link-primary" href="/upload">+ Upload CV</Link></div>
      </div>
      <section className="card pipeline-filter-card" aria-label="Pipeline filters">
        <div className="pipeline-filter-heading"><div><strong>Find your candidates</strong><small>Choose a job or search across the entire pipeline.</small></div><span className="chip">{filtered.length} {filtered.length === 1 ? "card" : "cards"}</span></div>
        <div className="pipeline-filter-grid">
          <div className="pipeline-job-filter">
            <label htmlFor="pipeline-job">Job</label>
            <select id="pipeline-job" value={selectedJobId} onChange={(event) => setSelectedJobId(Number(event.target.value))} disabled={jobsQuery.isPending}>
              <option value={0}>All jobs &amp; unassigned candidates</option>
              {filteredJobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            {jobs.length > 5 && <input className="pipeline-job-search" aria-label="Find a job" placeholder="Filter job titles…" value={jobSearch} onChange={(event) => setJobSearch(event.target.value)} />}
          </div>
          <div className="pipeline-candidate-filter">
            <label htmlFor="pipeline-search">Search candidates</label>
            <div className="pipeline-search-input">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
              <input id="pipeline-search" type="search" placeholder="Name, email, skill or job title" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            </div>
            <small>Try “Python” or a candidate’s name. Multiple words narrow the results.</small>
          </div>
          <button className="btn-outline pipeline-filter-reset" disabled={!keyword && !selectedJobId && !jobSearch} onClick={() => { setKeyword(""); setJobSearch(""); setSelectedJobId(0); }}>Reset filters</button>
        </div>
        <div className="pipeline-filter-summary" aria-live="polite"><span>{selectedJob?.title || "All jobs"}{keyword.trim() ? ` · “${keyword.trim()}”` : ""}</span><small>Drag a card or use its stage menu. Each job application moves independently.</small></div>
      </section>
      <div className="pipeline-stage-summary" aria-label="Stage totals">
        {CANDIDATE_STATUSES.map((stage) => <div key={stage}><span className={`status-badge status-${stage}`}>{formatCandidateStatus(stage)}</span><strong>{byStage[stage].length}</strong></div>)}
      </div>
      {(boardQuery.isError || jobsQuery.isError) && <div className="inline-alert" role="alert">Could not load the pipeline. <button className="text-button" onClick={() => { boardQuery.refetch(); jobsQuery.refetch(); }}>Try again</button></div>}
      {boardQuery.isPending ? <div className="empty-state" role="status">Loading pipeline…</div> : <>
        {!filtered.length && <div className="empty-state"><strong>No matching candidates</strong><small>{candidates.length ? "Try another name, skill, or job filter." : "Upload a CV or add candidates to a job to get started."}</small></div>}
        <div className="kanban-board" aria-busy={mutation.isPending}>
          {CANDIDATE_STATUSES.map((stage) => <PipelineColumn
            key={stage} stage={stage} items={byStage[stage]} count={byStage[stage].length}
            visible={visibleByStage[stage] || VISIBLE_STEP} active={overStage === stage} moving={mutation.isPending}
            onDragOver={(event) => { event.preventDefault(); if (dragKey && !mutation.isPending) setOverStage(stage); }}
            onDragLeave={() => setOverStage((current) => current === stage ? null : current)}
            onDrop={() => { const key = dragKey; setDragKey(null); setOverStage(null); if (key) void moveToStage(key, stage); }}
            onMove={moveToStage} onDragStart={setDragKey} onDragEnd={() => { setDragKey(null); setOverStage(null); }}
            onLoadMore={() => setVisibleByStage((previous) => ({ ...previous, [stage]: (previous[stage] || VISIBLE_STEP) + VISIBLE_STEP }))}
          />)}
        </div>
      </>}
    </div>
  );
}
