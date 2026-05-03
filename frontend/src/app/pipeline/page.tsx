"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../../lib/api";
import { notify } from "../../lib/toast";
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
  const [overStage, setOverStage] = useState<CandidateStatus | null>(null);
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
    setOverStage(null);
    notify(`Candidate moved to ${label(stage)}`, "success");
  };

  const moveToStage = async (candidateId: number, stage: CandidateStatus) => {
    await apiPatch(`/api/candidates/${candidateId}`, { status: stage });
    setCandidates((prev) => prev.map((c) => (c.id === candidateId ? { ...c, status: stage } : c)));
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
          <div
            key={stage}
            className={`kanban-column ${overStage === stage ? "drop-active" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOverStage(stage); }}
            onDragLeave={() => setOverStage((prev) => (prev === stage ? null : prev))}
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
                  <small>{(c.parsed_json as any)?.current_title || "Role not set"} • {c.years_of_experience || 0} yrs</small>
                  <small>{c.email || "No email"}</small>
                  <small>Match {Number((c.parsed_json as any)?.match_score || 0)}% • Last active {(c.parsed_json as any)?.timeline?.length ? `${(c.parsed_json as any).timeline.length} events` : "new"}</small>
                  <div className="chip-wrap" style={{ marginTop: 8 }}>
                    {(c.skills || []).slice(0, 3).map((s) => (
                      <span className="chip" key={`${c.id}-${s}`}>
                        {s}
                      </span>
                    ))}
                  </div>
                  <div className="toolbar-actions card-hover-actions" style={{ marginTop: 10 }}>
                    <Link href={`/candidates/${c.id}`} className="chip">View</Link>
                    <select value={c.status || "applied"} onChange={(e) => moveToStage(c.id, e.target.value as CandidateStatus)} style={{ width: "auto" }}>
                      {STAGES.map((s) => <option key={s} value={s}>Move to {label(s)}</option>)}
                    </select>
                    <button className="btn-outline" style={{ width: "auto" }} onClick={() => moveToStage(c.id, "rejected")}>Reject</button>
                  </div>
                </div>
              ))}
              {!byStage[stage].length && <div className="empty-state"><strong>No candidates yet</strong><small>Add or upload candidates to start this stage.</small><div className="toolbar-actions"><Link className="chip" href="/upload">Upload CV</Link><Link className="chip" href="/">Add Candidate</Link></div></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
