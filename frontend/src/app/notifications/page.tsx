"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";

export default function NotificationsPage() {
  const [mentions, setMentions] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const data = await apiGet<{ mentions: any[] }>("/api/candidates/mentions");
      setMentions(data.mentions || []);
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
          {!mentions.length && <small>No notifications yet.</small>}
        </div>
      </div>
    </div>
  );
}
