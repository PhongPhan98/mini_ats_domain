"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import { notify } from "../../lib/toast";
import type { Application, Candidate } from "../../components/types";
import { useMe } from "../../lib/me";

type Job = { id: number; title: string };
type Offer = { id: number; application_id: number; candidate_name?: string; job_title?: string; title: string; salary_amount?: number; currency: string; start_date?: string; status: string; created_at: string };

const NEXT: Record<string, { value: string; label: string }[]> = {
  draft: [{ value: "pending_approval", label: "Request approval" }],
  pending_approval: [{ value: "approved", label: "Approve" }, { value: "rejected", label: "Reject" }],
  approved: [{ value: "sent", label: "Mark sent" }],
  sent: [{ value: "accepted", label: "Accepted" }, { value: "declined", label: "Declined" }],
  rejected: [{ value: "draft", label: "Return to draft" }],
};

export default function OffersPage() {
  const { me } = useMe();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applicationId, setApplicationId] = useState("");
  const [title, setTitle] = useState("");
  const [salary, setSalary] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [startDate, setStartDate] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => {
    const [offerRows, appRows, candidateRows, jobRows] = await Promise.all([
      apiGet<Offer[]>("/api/offers"), apiGet<Application[]>("/api/applications"),
      apiGet<Candidate[]>("/api/candidates"), apiGet<Job[]>("/api/jobs"),
    ]);
    setOffers(offerRows); setApplications(appRows); setCandidates(candidateRows); setJobs(jobRows);
  };
  useEffect(() => { load(); }, []);

  const names = useMemo(() => Object.fromEntries(candidates.map((candidate) => [candidate.id, candidate.name || `Candidate #${candidate.id}`])), [candidates]);
  const jobNames = useMemo(() => Object.fromEntries(jobs.map((job) => [job.id, job.title])), [jobs]);
  const existing = new Set(offers.map((offer) => offer.application_id));

  const create = async () => {
    if (!applicationId || !title.trim()) return notify("Select an application and enter an offer title", "error");
    await apiPost("/api/offers", { application_id: Number(applicationId), title: title.trim(), salary_amount: salary ? Number(salary) : null, currency, start_date: startDate ? new Date(startDate).toISOString() : null });
    setTitle(""); setSalary(""); setApplicationId(""); setShowCreate(false); await load(); notify("Offer draft created", "success");
  };

  const transition = async (id: number, status: string) => {
    try { await apiPatch(`/api/offers/${id}/status`, { status }); await load(); notify("Offer updated", "success"); }
    catch (error) { notify(error instanceof Error ? error.message : "Could not update offer", "error"); }
  };

  return <div className="grid page-enter">
    <div className="card"><div className="toolbar"><div><h2 style={{ margin: 0 }}>Offers</h2><small>Create, approve, send, and record offer decisions.</small></div><button style={{ width: "auto" }} onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Cancel" : "Create offer"}</button></div></div>
    {showCreate && <div className="card grid"><label>Job application<select value={applicationId} onChange={(event) => setApplicationId(event.target.value)}><option value="">Select application</option>{applications.filter((application) => !existing.has(application.id) && ["interview", "offer"].includes(application.stage)).map((application) => <option key={application.id} value={application.id}>{names[application.candidate_id]} · {jobNames[application.job_id]} · {application.stage}</option>)}</select></label><label>Offer title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Software Engineer offer" /></label><div className="form-grid-2"><label>Salary<input type="number" min={0} value={salary} onChange={(event) => setSalary(event.target.value)} /></label><label>Currency<input maxLength={8} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} /></label></div><label>Proposed start date<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><button onClick={create}>Save draft</button></div>}
    <div className="card"><div className="job-list">{offers.map((offer) => <div className="job-item" key={offer.id}><div><div className="toolbar-actions"><strong>{offer.candidate_name}</strong><span className="chip">{offer.status.replaceAll("_", " ")}</span></div><div>{offer.job_title} · {offer.title}</div><small>{offer.salary_amount ? `${offer.currency} ${offer.salary_amount.toLocaleString()}` : "Salary not set"}{offer.start_date ? ` · Starts ${new Date(offer.start_date).toLocaleDateString()}` : ""}</small></div><div className="toolbar-actions">{(NEXT[offer.status] || []).filter((action) => !["approved", "rejected"].includes(action.value) || ["admin", "hiring_manager"].includes(me?.role || "")).map((action) => <button key={action.value} className={action.value === "approved" || action.value === "accepted" ? "" : "btn-outline"} style={{ width: "auto" }} onClick={() => transition(offer.id, action.value)}>{action.label}</button>)}</div></div>)}{!offers.length && <div className="empty-state"><strong>No offers yet</strong><small>Create an offer when an application reaches the interview or offer stage.</small></div>}</div></div>
  </div>;
}
