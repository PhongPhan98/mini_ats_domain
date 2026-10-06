"use client";
import Link from "next/link";
import type { Candidate, CandidateStatus } from "./types";
import { formatCandidateStatus } from "../lib/candidates";

export default function CandidateCard({ c, stages, onMove, onDragStart, onDragEnd, moving }: {
  c: Candidate; stages: CandidateStatus[]; onMove: (key: string, stage: CandidateStatus) => void;
  onDragStart: (key: string) => void; onDragEnd: () => void; moving: boolean;
}) {
  const key = c.board_key || `candidate:${c.id}`;
  const editable = Boolean(c.can_move) && !moving;
  return (
    <article className="kanban-card" draggable={editable} onDragStart={(event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", key);
      onDragStart(key);
    }} onDragEnd={onDragEnd}>
      <Link className="kanban-title" href={`/candidates/${c.id}`}>{c.name || `Candidate #${c.id}`}</Link>
      <small>{c.parsed_json?.current_title || "Role not stated"}{c.years_of_experience != null ? ` · ${c.years_of_experience} yrs` : ""}</small>
      <small>{c.email || "No email"}</small>
      <span className="pipeline-job-badge">{c.job_title || "Unassigned candidate"}</span>
      {c.match_score != null && <small>Match {c.match_score}%</small>}
      <div className="chip-wrap" style={{ marginTop: 8 }}>{(c.skills || []).slice(0, 3).map((skill) => <span className="chip" key={skill}>{skill}</span>)}</div>
      <div className="pipeline-card-actions">
        <Link href={`/candidates/${c.id}`} className="chip">View profile</Link>
        <select aria-label={`Stage for ${c.name || "candidate"}${c.job_title ? ` at ${c.job_title}` : ""}`} disabled={!editable} value={c.status || "applied"} onChange={(event) => onMove(key, event.target.value as CandidateStatus)}>
          {stages.map((stage) => <option key={stage} value={stage}>{formatCandidateStatus(stage)}</option>)}
        </select>
      </div>
    </article>
  );
}
