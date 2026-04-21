"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../../../lib/api";
import type { Candidate, CandidateStatus, TimelineEvent } from "../../../components/types";

type CandidateForm = {
  name: string;
  email: string;
  phone: string;
  status: CandidateStatus;
  years_of_experience: string;
  skills_text: string;
  education_text: string;
  previous_companies_text: string;
  summary: string;
  note: string;
};

const STATUS_OPTIONS: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];

function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function toForm(c: Candidate): CandidateForm {
  return {
    name: c.name || "",
    email: c.email || "",
    phone: c.phone || "",
    status: c.status || "applied",
    years_of_experience: c.years_of_experience?.toString() || "",
    skills_text: (c.skills || []).join(", "),
    education_text: (c.education || []).join("\n"),
    previous_companies_text: (c.previous_companies || []).join("\n"),
    summary: c.summary || "",
    note: "",
  };
}

function normalizeCommaList(text: string): string[] {
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

function normalizeLineList(text: string): string[] {
  return text.split("\n").map((s) => s.trim()).filter(Boolean);
}

function timelineOf(candidate: Candidate): TimelineEvent[] {
  return (candidate.parsed_json?.timeline || []).slice().reverse();
}

export default function CandidateDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [form, setForm] = useState<CandidateForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [candidateId, setCandidateId] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resolved = await params;
        if (cancelled) return;
        setCandidateId(resolved.id);
        const data = await apiGet<Candidate>(`/api/candidates/${resolved.id}`);
        if (cancelled) return;
        setCandidate(data);
        setForm(toForm(data));
      } catch (e: any) {
        if (!cancelled) setError(e.message || "Failed to load candidate");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params]);

  const canSave = useMemo(() => !!form && !saving, [form, saving]);
  const updateField = (key: keyof CandidateForm, value: string) => setForm((prev) => (prev ? { ...prev, [key]: value } : prev));

  const onSave = async () => {
    if (!form || !candidateId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        name: form.name || null,
        email: form.email || null,
        phone: form.phone || null,
        status: form.status,
        years_of_experience: form.years_of_experience ? Number(form.years_of_experience) : null,
        skills: normalizeCommaList(form.skills_text),
        education: normalizeLineList(form.education_text),
        previous_companies: normalizeLineList(form.previous_companies_text),
        summary: form.summary || null,
        notes: form.note || null,
      };
      const updated = await apiPatch<Candidate>(`/api/candidates/${candidateId}`, payload);
      setCandidate(updated);
      const next = toForm(updated);
      next.note = "";
      setForm(next);
      setMessage("Candidate updated successfully");
    } catch (e: any) {
      setError(e.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="card">Loading candidate...</div>;
  if (error && !candidate) return <div className="card"><p style={{ color: "red" }}>{error}</p><Link href="/">Back</Link></div>;
  if (!form || !candidate) return <div className="card"><p>Candidate not found.</p><Link href="/">Back</Link></div>;

  return (
    <div className="grid page-enter">
      <div className="card"><Link href="/">← Back</Link><h2 style={{ marginTop: 12 }}>Candidate Detail Edit</h2></div>
      <div className="card">
        <div className="grid grid-2">
          <div><label>Name</label><input value={form.name} onChange={(e) => updateField("name", e.target.value)} /></div>
          <div><label>Email</label><input value={form.email} onChange={(e) => updateField("email", e.target.value)} /></div>
          <div><label>Phone</label><input value={form.phone} onChange={(e) => updateField("phone", e.target.value)} /></div>
          <div><label>Stage</label><select value={form.status} onChange={(e) => updateField("status", e.target.value)}>{STATUS_OPTIONS.map((s) => <option key={s} value={s}>{formatStatus(s)}</option>)}</select></div>
          <div><label>Years of experience</label><input type="number" min={0} value={form.years_of_experience} onChange={(e) => updateField("years_of_experience", e.target.value)} /></div>
        </div>
        <div style={{ marginTop: 12 }}><label>Skills (comma-separated)</label><input value={form.skills_text} onChange={(e) => updateField("skills_text", e.target.value)} /></div>
        <div style={{ marginTop: 12 }}><label>Education</label><textarea rows={4} value={form.education_text} onChange={(e) => updateField("education_text", e.target.value)} /></div>
        <div style={{ marginTop: 12 }}><label>Previous companies</label><textarea rows={4} value={form.previous_companies_text} onChange={(e) => updateField("previous_companies_text", e.target.value)} /></div>
        <div style={{ marginTop: 12 }}><label>Summary</label><textarea rows={6} value={form.summary} onChange={(e) => updateField("summary", e.target.value)} /></div>
        <div style={{ marginTop: 12 }}><label>Add note update</label><textarea rows={3} value={form.note} onChange={(e) => updateField("note", e.target.value)} /></div>
        <div style={{ marginTop: 16 }}><button onClick={onSave} disabled={!canSave}>{saving ? "Saving..." : "Save changes"}</button></div>
        {message && <p style={{ color: "green" }}>{message}</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>
      <div className="card"><h3>Candidate Timeline</h3><div className="timeline">{timelineOf(candidate).map((event, idx) => <div className="timeline-item" key={`${event.timestamp}-${idx}`}><div className="timeline-dot" /><div><div className="timeline-title">{formatStatus(event.type)}</div><div>{event.value}</div><small>{event.timestamp}</small></div></div>)}</div></div>
    </div>
  );
}
