"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";

export default function NotificationsPage() {
  const [mentions, setMentions] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const [m, r] = await Promise.all([
        apiGet<{ mentions: any[] }>("/api/candidates/notifications/mentions"),
        apiGet<{ requests: any[] }>("/api/candidates/ownership/requests?scope=sent"),
      ]);
      setMentions(m.mentions || []);
      setRequests((r.requests || []).filter((x) => x.status !== "pending"));
      localStorage.setItem("miniats_notif_seen_at", new Date().toISOString());
    })();
  }, []);

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Notifications</h2>
        <small>Mentions where teammates tagged you in candidate comments.</small>
      </div>

      <div className="card">
        <div className="timeline">
          {mentions.map((m) => (
            <div key={m.comment_id} className="timeline-item">
              <div className="timeline-dot" />
              <div>
                <div className="timeline-title">Mentioned in candidate #{m.candidate_id}</div>
                <div>{m.body}</div>
                <small>{m.created_at}</small>
                <div style={{ marginTop: 6 }}>
                  <Link className="chip" href={`/candidates/${m.candidate_id}`}>Open Candidate</Link>
                </div>
              </div>
            </div>
          ))}
          {!mentions.length && <small>No mention notifications yet.</small>}
        </div>
      </div>

      <div className="card">
        <h3>Ownership Request Updates</h3>
        <div className="timeline">
          {requests.map((r) => (
            <div key={r.id} className="timeline-item">
              <div className="timeline-dot" />
              <div>
                <div className="timeline-title">Candidate #{r.candidate_id} — {r.status}</div>
                <div>Your request to transfer ownership is <strong>{r.status}</strong>.</div>
                <small>{r.updated_at || r.created_at}</small>
                <div style={{ marginTop: 6 }}><Link className="chip" href={`/candidates/${r.candidate_id}#req-${r.id}`}>Open Candidate</Link></div>
              </div>
            </div>
          ))}
          {!requests.length && <small>No ownership updates yet.</small>}
        </div>
      </div>
    </div>
  );
}
