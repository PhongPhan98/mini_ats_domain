"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";

type ActivityEvent = { candidate_id: number; candidate_name?: string; type?: string; value?: string; timestamp?: string };
export default function ActivityPage() { const [events,setEvents]=useState<ActivityEvent[]>([]); const [loading,setLoading]=useState(true);
useEffect(()=>{(async()=>{try{const data=await apiGet<{events:ActivityEvent[]}>("/api/activity?limit=300");setEvents(data.events||[]);}finally{setLoading(false);}})();},[]);
return <div className="grid page-enter"><div className="card"><h2 style={{marginTop:0}}>Activity Log</h2><small>Track candidate updates, stage moves, notes, and collaboration events.</small></div><div className="card">{loading?<small>Loading activity...</small>:null}{!loading&&!events.length?<div className="empty-state"><strong>No data yet</strong><small>Activity will appear after candidate actions.</small></div>:null}<div className="timeline">{events.map((e,i)=><div key={`${e.candidate_id}-${e.timestamp}-${i}`} className="timeline-item"><div className="timeline-dot"/><div><div><strong>{e.type||"event"}</strong> • <Link href={`/candidates/${e.candidate_id}`}>{e.candidate_name||`Candidate #${e.candidate_id}`}</Link></div><div>{e.value||"-"}</div><small>{e.timestamp?new Date(e.timestamp).toLocaleString():"-"}</small></div></div>)}</div></div></div>; }
