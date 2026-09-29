"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl } from "../../../lib/api";

type PublicJob = {
  title: string;
  description?: string;
  requirements: string;
  department?: string;
  location?: string;
  employment_type?: string;
  salary_min?: number;
  salary_max?: number;
  currency?: string;
  closes_at?: string;
};

const MAX_BYTES = 20 * 1024 * 1024;

export default function PublicJobPage({ params }: { params: Promise<{ slug: string }> }) {
  const [slug, setSlug] = useState("");
  const [job, setJob] = useState<PublicJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [source, setSource] = useState("career_site");
  const [consent, setConsent] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      const route = await params;
      if (!active) return;
      setSlug(route.slug);
      try {
        const response = await fetch(apiUrl(`/api/public/jobs/${route.slug}`), { cache: "no-store" });
        if (!response.ok) throw new Error(response.status === 404 ? "This role is no longer accepting applications." : "Could not load this role.");
        setJob(await response.json());
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Could not load this role.");
      } finally {
        setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [params]);

  const chooseFile = (next: File | null) => {
    setError("");
    if (!next) return setFile(null);
    const extension = next.name.toLowerCase().split(".").pop();
    if (!extension || !["pdf", "docx"].includes(extension)) return setError("Upload a PDF or DOCX CV.");
    if (next.size > MAX_BYTES) return setError("Your CV must be 20 MB or smaller.");
    setFile(next);
  };

  const onApply = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("name", name.trim());
      form.append("email", email.trim());
      form.append("phone", phone.trim());
      form.append("source", source);
      form.append("consent", String(consent));
      if (file) form.append("file", file);
      const response = await fetch(apiUrl(`/api/public/jobs/${slug}/apply`), { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "We could not submit your application.");
      }
      setDone(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "We could not submit your application.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="public-job-state"><div className="spinner" /><p>Loading role…</p></div>;
  if (!job) return <div className="public-job-state"><h1>Role unavailable</h1><p>{error}</p></div>;
  if (done) return <div className="public-job-state success-panel"><span className="success-mark">✓</span><h1>Application received</h1><p>Thank you, {name}. The hiring team will review your application and contact you by email.</p></div>;

  const salary = job.salary_min && job.salary_max ? `${job.currency || ""} ${job.salary_min.toLocaleString()} – ${job.salary_max.toLocaleString()}` : null;
  return (
    <div className="career-page page-enter">
      <section className="career-hero">
        <span className="eyebrow">Career opportunity</span>
        <h1>{job.title}</h1>
        <div className="job-facts">
          {job.department && <span>{job.department}</span>}
          {job.location && <span>{job.location}</span>}
          {job.employment_type && <span>{job.employment_type}</span>}
          {salary && <span>{salary}</span>}
        </div>
        {job.closes_at && <small>Applications close {new Date(job.closes_at).toLocaleDateString()}</small>}
      </section>

      <div className="career-layout">
        <article className="card job-description">
          {job.description && <><h2>About the role</h2><p className="preline">{job.description}</p></>}
          <h2>What we’re looking for</h2>
          <p className="preline">{job.requirements}</p>
        </article>

        <form className="card application-form" onSubmit={onApply}>
          <div><span className="eyebrow">Apply now</span><h2>Send your application</h2><p>Usually takes less than two minutes.</p></div>
          <label>Full name *<input autoComplete="name" required minLength={2} maxLength={255} value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>Email address *<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Phone number<input type="tel" autoComplete="tel" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label>How did you hear about us?<select value={source} onChange={(event) => setSource(event.target.value)}><option value="career_site">Company careers page</option><option value="linkedin">LinkedIn</option><option value="referral">Employee referral</option><option value="job_board">Job board</option><option value="other">Other</option></select></label>
          <label className="cv-picker"><span>CV <small>PDF or DOCX, up to 20 MB</small></span><input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => chooseFile(event.target.files?.[0] || null)} />{file && <strong>{file.name}</strong>}</label>
          <label className="consent-row"><input type="checkbox" required checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>I consent to the hiring team processing my information for this application under the <Link href="/privacy" target="_blank">candidate privacy notice</Link>. *</span></label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button type="submit" disabled={submitting || !consent}>{submitting ? "Submitting…" : "Submit application"}</button>
          <small>Your information is available only to the hiring team.</small>
        </form>
      </div>
    </div>
  );
}
