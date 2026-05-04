"use client";
import Link from "next/link";
import type { Candidate, CandidateStatus } from "./types";

export default function CandidateCard({ c, stages, onMove, onDragStart }: { c: Candidate; stages: CandidateStatus[]; onMove: (id: number, s: CandidateStatus) => void; onDragStart: (id:number)=>void }) {
  return (
    <div className="kanban-card" draggable onDragStart={() => onDragStart(c.id)}>
      <div className="kanban-title">{c.name || `Candidate #${c.id}`}</div>
      <small>{(c.parsed_json as any)?.current_title || "Role not set"} • {c.years_of_experience || 0} yrs</small>
      <small>{c.email || "No email"}</small>
      <small>Match {Number((c.parsed_json as any)?.match_score || 0)}% • Last active {(c.parsed_json as any)?.timeline?.length ? `${(c.parsed_json as any).timeline.length} events` : "new"}</small>
      <div className="chip-wrap" style={{ marginTop: 8 }}>
        {(c.parsed_json as any)?.applied_job_title ? <span className="chip">Job: {(c.parsed_json as any)?.applied_job_title}</span> : null}
        {(c.skills || []).slice(0, 3).map((s) => <span className="chip" key={`${c.id}-${s}`}>{s}</span>)}
      </div>
      <div className="toolbar-actions card-hover-actions" style={{ marginTop: 10 }}>
        <Link href={`/candidates/${c.id}`} className="chip">View</Link>
        <select value={c.status || "applied"} onChange={(e) => onMove(c.id, e.target.value as CandidateStatus)} style={{ width: "auto" }}>
          {stages.map((s) => <option key={s} value={s}>Move to {s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
        </select>
        <button className="btn-outline" style={{ width: "auto" }} onClick={() => onMove(c.id, "rejected")}>Reject</button>
      </div>
    </div>
  );
}
