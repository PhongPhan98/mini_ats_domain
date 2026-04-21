"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../../lib/api";
import type { Candidate, CandidateStatus } from "../../components/types";

const STAGES: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];

function label(s: CandidateStatus) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function PipelinePage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [dragId, setDragId] = useState<number | null>(null);

  const load = async () => {
    const data = await apiGet<Candidate[]>("/api/candidates");
    setCandidates(data);
  };

  useEffect(() => {
    load();
  }, []);

  const byStage = useMemo(() => {
    const map: Record<string, Candidate[]> = {};
    for (const s of STAGES) map[s] = [];
    for (const c of candidates) {
      const s = STAGES.includes(c.status) ? c.status : "applied";
      map[s].push(c);
    }
    return map;
  }, [candidates]);

  const onDropToStage = async (stage: CandidateStatus) => {
    if (!dragId) return;
    await apiPatch(`/api/candidates/${dragId}`, { status: stage });
    setCandidates((prev) => prev.map((c) => (c.id === dragId ? { ...c, status: stage } : c)));
    setDragId(null);
  };

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2>Recruitment Pipeline</h2>
        <small>Drag candidates between stages to update pipeline status.</small>
      </div>

      <div className="kanban-board">
        {STAGES.map((stage) => (
          <div
            key={stage}
            className="kanban-column"
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => onDropToStage(stage)}
          >
            <div className="kanban-column-head">
              <strong>{label(stage)}</strong>
              <span className="chip">{byStage[stage].length}</span>
            </div>

            <div className="kanban-cards">
              {byStage[stage].map((c) => (
                <div
                  key={c.id}
                  className="kanban-card"
                  draggable
                  onDragStart={() => setDragId(c.id)}
                >
                  <div className="kanban-title">{c.name || `Candidate #${c.id}`}</div>
                  <small>{c.email || "No email"}</small>
                  <div className="chip-wrap" style={{ marginTop: 8 }}>
                    {(c.skills || []).slice(0, 3).map((s) => (
                      <span className="chip" key={`${c.id}-${s}`}>
                        {s}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <Link href={`/candidates/${c.id}`} className="chip">
                      Open
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
