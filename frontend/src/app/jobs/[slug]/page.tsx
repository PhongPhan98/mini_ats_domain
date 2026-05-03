"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "../../../lib/api";

export default function PublicJobPage({ params }: { params: Promise<{ slug: string }> }) {
  const [slug, setSlug] = useState("");
  const [job, setJob] = useState<any>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    (async () => {
      const p = await params;
      setSlug(p.slug);
      const res = await fetch(apiUrl(`/api/public/jobs/${p.slug}`));
      if (res.ok) setJob(await res.json());
    })();
  }, [params]);

  const onApply = async () => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("email", email);
    fd.append("phone", phone);
    if (file) fd.append("file", file);
    const res = await fetch(apiUrl(`/api/public/jobs/${slug}/apply`), { method: "POST", body: fd });
    if (res.ok) setDone(true);
  };

  if (!job) return <div className="card">Loading public job...</div>;
  if (done) return <div className="card"><h2>Application submitted</h2><small>Thank you! Our team will contact you soon.</small></div>;

  return (
    <div className="grid page-enter">
      <div className="card">
        <h1 style={{ marginTop: 0 }}>{job.title}</h1>
        <pre style={{ whiteSpace: "pre-wrap" }}>{job.requirements || ""}</pre>
      </div>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Apply for this job</h3>
        <div className="grid">
          <input placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Your email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Your phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button onClick={onApply} disabled={!name || !email}>Submit Application</button>
        </div>
      </div>
    </div>
  );
}
