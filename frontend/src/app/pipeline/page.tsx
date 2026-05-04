"use client";

import Link from "next/link";
import PipelineColumn from "../../components/PipelineColumn";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch } from "../../lib/api";
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
  const [visibleByStage, setVisibleByStage] = useState<Record<string, number>>({});
  const { t } = useAppLanguage();

  const qc = useQueryClient();
  const { data: candidates = [] } = useQuery({ queryKey: ["pipeline-candidates"], queryFn: () => apiGet<Candidate[]>("/api/candidates") });

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    if (!q) return candidates;
    return candidates.filter((c) => {
      const txt = `${c.name || ""} ${c.email || ""} ${(c.skills || []).join(" ")}`.toLowerCase();
      return txt.includes(q);
    });
  }, [candidates, keyword]);

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
    mutationFn: ({ candidateId, stage }: { candidateId: number; stage: CandidateStatus }) => apiPatch(`/api/candidates/${candidateId}/stage`, { stage }),
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
          </div>
          <input
            style={{ maxWidth: 320 }}
            placeholder={t("search_placeholder")}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
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
