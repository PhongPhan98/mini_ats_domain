"use client";
import type { DragEvent } from "react";
import type { Candidate, CandidateStatus } from "./types";
import CandidateCard from "./CandidateCard";
import { CANDIDATE_STATUSES, formatCandidateStatus } from "../lib/candidates";

export default function PipelineColumn({ stage, items, count, visible, onLoadMore, onDrop, onDragOver, onDragLeave, onMove, active, onDragStart, onDragEnd, moving }: {
  stage: CandidateStatus; items: Candidate[]; count: number; visible: number; moving: boolean;
  onLoadMore: () => void; onDrop: () => void; onDragOver: (event: DragEvent<HTMLDivElement>) => void;
  onDragLeave: () => void; onMove: (key: string, stage: CandidateStatus) => void;
  active: boolean; onDragStart: (key: string) => void; onDragEnd: () => void;
}) {
  return <div className={`kanban-column ${active ? "drop-active" : ""}`} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={(event) => { event.preventDefault(); onDrop(); }}>
    <div className="kanban-column-head"><strong>{formatCandidateStatus(stage)}</strong><span className={`status-badge status-${stage}`}>{count}</span></div>
    <div className="kanban-cards">
      {items.slice(0, visible).map((candidate) => <CandidateCard key={candidate.board_key} c={candidate} stages={CANDIDATE_STATUSES} onMove={onMove} onDragStart={onDragStart} onDragEnd={onDragEnd} moving={moving} />)}
      {!items.length && <div className="pipeline-empty-column">Drop a card here</div>}
      {items.length > visible && <button className="btn-outline" onClick={onLoadMore}>Load more ({items.length - visible})</button>}
    </div>
  </div>;
}
