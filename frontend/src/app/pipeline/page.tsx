"use client";

import Link from "next/link";
import PipelineColumn from "../../components/PipelineColumn";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, updateCandidateStage, getJobCandidates } from "../../lib/api";
import { notify } from "../../lib/toast";
import { useAppLanguage } from "../../lib/language";
import type { Candidate, CandidateStatus } from "../../components/types";

const STAGES: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];
const VISIBLE_STEP = 30;

function label(s: CandidateStatus) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function PipelinePage() {
  const [dragId, setDragId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const [overStage, setOverStage] = useState<CandidateStatus | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number>(0);
  const [visibleByStage, setVisibleByStage] = useState<Record<string, number>>({});
  const { t } = useAppLanguage();

  const qc = useQueryClient();
  const { data: jobs = [] } = useQuery({ queryKey: ["pipeline-jobs"], queryFn: () => apiGet<any[]>("/api/jobs") });
  const { data: candidates = [] } = useQuery({ queryKey: ["pipeline-candidates", selectedJobId], queryFn: async () => {
    if (!selectedJobId) return apiGet<Candidate[]>("/api/candidates");
    const data = await getJobCandidates(selectedJobId);
    return (data.candidates || []) as Candidate[];
  } });

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    if (!q) return candidates;
    return candidates.filter((c) => {
      const txt = `${c.name || ""} ${c.email || ""} ${(c.skills || []).join(" ")}`.toLowerCase();
      return txt.includes(q);
    });
  }, [candidates, keyword]);

  const avgTimeToHire = useMemo(() => {
    const hired = candidates.filter((c) => (c.status || "") === "hired" && c.created_at);
    if (!hired.length) return 0;
    const days = hired.map((c:any) => (Date.now() - new Date(c.created_at).getTime()) / 86400000);
    return Math.round((days.reduce((a,b)=>a+b,0)/days.length)*10)/10;
  }, [candidates]);

  const byStage = useMemo(() => {
    const map: Record<string, Candidate[]> = {};
    for (const s of STAGES) map[s] = [];
    for (const c of filtered) {
      const s = STAGES.includes(c.status) ? c.status : "applied";
      map[s].push(c);
    }
    return map;
  }, [filtered]);


  useEffect(() => {
    setVisibleByStage((prev) => {
      const next = { ...prev };
      for (const st of STAGES) { if (!next[st]) next[st] = VISIBLE_STEP; }
      return next;
    });
  }, [candidates.length]);

  const stageMutation = useMutation({
    mutationFn: ({ candidateId, stage }: { candidateId: number; stage: CandidateStatus }) => updateCandidateStage(candidateId, stage),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline-candidates"] }),
  });

  const onDropToStage = async (stage: CandidateStatus) => {
    if (!dragId) return;
    await stageMutation.mutateAsync({ candidateId: dragId, stage });
    setDragId(null);
    setOverStage(null);
    notify(`Candidate moved to ${label(stage)}`, "success");
  };

  const moveToStage = async (candidateId: number, stage: CandidateStatus) => {
    await stageMutation.mutateAsync({ candidateId, stage });
    notify(`Candidate moved to ${label(stage)}`, "success");
  };

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <h2 style={{ margin: 0 }}>{t("pipeline_title")}</h2>
            <small>{t("pipeline_hint")}</small>
            <small>Time-to-hire (selection): {avgTimeToHire} days</small>
          </div>
          <div className="toolbar-actions">
            <select value={selectedJobId} onChange={(e) => setSelectedJobId(Number(e.target.value || 0))} style={{ width: "auto" }}>
              <option value={0}>All Jobs</option>
              {jobs.map((j: any) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
            <input
              style={{ maxWidth: 320 }}
              placeholder={t("search_placeholder")}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div>
            <h3 style={{ margin: 0 }}>Pipeline workflow</h3>
            <small>Drag candidates across stages or use quick Move to actions.</small>
          </div>
          <div className="toolbar-actions">
            <Link className="chip" href="/jobs">Create Job</Link>
            <Link className="chip" href="/upload">Upload CV</Link>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Job Funnel Snapshot</h3>
        <div className="grid" style={{ gap: 8 }}>
          {STAGES.map((s) => {
            const c = byStage[s].length;
            const total = Math.max(1, candidates.length);
            const pct = Math.max(2, Math.min(100, Math.round((c * 100) / total)));
            return <div key={`funnel-${s}`}><small>{label(s)} • {c}</small><div className="score-bar" style={{ width: "100%" }}><span style={{ width: `${pct}%` }} /></div></div>;
          })}
        </div>
      </div>

      <div className="kanban-board">
        {STAGES.map((stage) => (
          <PipelineColumn
            key={stage}
            stage={stage}
            items={byStage[stage]}
            count={byStage[stage].length}
            visible={visibleByStage[stage] || VISIBLE_STEP}
            active={overStage === stage}
            onDragOver={(e) => { e.preventDefault(); setOverStage(stage); }}
            onDragLeave={() => setOverStage((prev) => (prev === stage ? null : prev))}
            onDrop={() => onDropToStage(stage)}
            onMove={moveToStage}
            onLoadMore={() => setVisibleByStage((prev) => ({ ...prev, [stage]: (prev[stage] || VISIBLE_STEP) + VISIBLE_STEP }))}
            onDragStart={(id) => setDragId(id)}
          />
        ))}
      </div>
    </div>
  );
}
