"use client";
import Link from "next/link";
import type { Candidate, CandidateStatus } from "./types";
import CandidateCard from "./CandidateCard";

export default function PipelineColumn({ stage, items, count, visible, onLoadMore, onDrop, onDragOver, onDragLeave, onMove, active, onDragStart }: { stage: CandidateStatus; items: Candidate[]; count: number; visible: number; onLoadMore: () => void; onDrop: () => void; onDragOver: (e:any)=>void; onDragLeave: ()=>void; onMove: (id:number,s:CandidateStatus)=>void; active:boolean; onDragStart:(id:number)=>void; }) {
  const label = stage.charAt(0).toUpperCase()+stage.slice(1);
  return <div className={`kanban-column ${active ? "drop-active" : ""}`} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
    <div className="kanban-column-head"><strong>{label}</strong><span className={`status-badge status-${stage}`}>{count}</span></div>
    <div className="kanban-cards">
      {items.slice(0, visible).map((c) => <CandidateCard key={c.id} c={c} stages={["applied","screening","interview","offer","hired","rejected"]} onMove={onMove} onDragStart={onDragStart} />)}
      {!items.length && <div className="empty-state"><strong>No candidates yet</strong><small>Add or upload candidates to start this stage.</small><div className="toolbar-actions"><Link className="chip" href="/upload">Upload CV</Link><Link className="chip" href="/candidates">Add Candidate</Link></div></div>}
      {items.length > visible ? <button className="btn-outline" style={{ width: "100%" }} onClick={onLoadMore}>Load more ({items.length - visible} remaining)</button> : null}
    </div>
  </div>
}
