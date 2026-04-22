"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";
import type { Candidate, CandidateStatus } from "../../components/types";

const STAGES: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];

function label(s: CandidateStatus) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function PipelinePage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [dragId, setDragId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const { t } = useAppLanguage();

  const load = async () => {
    const data = await apiGet<Candidate[]>("/api/candidates");
    setCandidates(data);
  };

  useEffect(() => {
    load();
  }, []);

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

  const onDropToStage = async (stage: CandidateStatus) => {
    if (!dragId) return;
    await apiPatch(`/api/candidates/${dragId}`, { status: stage });
    setCandidates((prev) => prev.map((c) => (c.id === dragId ? { ...c, status: stage } : c)));
    setDragId(null);
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
              <span className={`status-badge status-${stage}`}>{byStage[stage].length}</span>
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
                  <div className="toolbar-actions" style={{ marginTop: 10 }}>
                    <Link href={`/candidates/${c.id}`} className="chip">
                      {t("open")}
                    </Link>
                    <span className={`status-badge status-${c.status || "applied"}`}>
                      {label(c.status || "applied")}
                    </span>
                  </div>
                </div>
              ))}
              {!byStage[stage].length && <small style={{ opacity: 0.7 }}>{t("no_candidates")}</small>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
