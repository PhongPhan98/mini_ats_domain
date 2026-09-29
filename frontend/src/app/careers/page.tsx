"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiUrl } from "../../lib/api";

type PublicJob = { id: number; title: string; slug: string; description?: string; department?: string; location?: string; employment_type?: string };

export default function CareersPage() {
  const [jobs, setJobs] = useState<PublicJob[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetch(apiUrl("/api/public/jobs"), { cache: "no-store" }).then((response) => response.ok ? response.json() : []).then(setJobs).finally(() => setLoading(false)); }, []);
  const visible = useMemo(() => { const value = query.trim().toLowerCase(); return value ? jobs.filter((job) => `${job.title} ${job.department || ""} ${job.location || ""}`.toLowerCase().includes(value)) : jobs; }, [jobs, query]);

  return <div className="career-page page-enter">
    <section className="career-hero careers-index"><span className="eyebrow">Build what comes next</span><h1>Find your next opportunity</h1><p>Explore open roles and apply in a few minutes.</p><input aria-label="Search open roles" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search role, team, or location" /></section>
    <section className="career-list" aria-live="polite">
      {loading ? <div className="public-job-state"><div className="spinner" /><p>Loading open roles…</p></div> : visible.map((job) => <Link className="card career-job-card" href={`/jobs/${job.slug}`} key={job.id}><div><span className="eyebrow">{job.department || "Open role"}</span><h2>{job.title}</h2><p>{job.description || "View the role details, requirements, and application form."}</p></div><div className="job-facts">{job.location && <span>{job.location}</span>}{job.employment_type && <span>{job.employment_type}</span>}<strong>View role →</strong></div></Link>)}
      {!loading && !visible.length && <div className="card empty-state"><strong>No matching roles</strong><small>Try another search or check back later.</small></div>}
    </section>
  </div>;
}
