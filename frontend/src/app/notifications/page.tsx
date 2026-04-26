"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";

type NotificationTab = "all" | "mentions" | "ownership";

const timeAgo = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - d);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const dd = Math.floor(h / 24);
  return `${dd}d ago`;
};

export default function NotificationsPage() {
  const router = useRouter();
  const [mentions, setMentions] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [tab, setTab] = useState<NotificationTab>("all");
  const [invitations, setInvitations] = useState<any[]>([]);

  const markAllRead = () => {
    localStorage.setItem("miniats_notif_seen_at", new Date().toISOString());
    window.dispatchEvent(new Event("storage"));
  };

  useEffect(() => {
    (async () => {
      const [m, r, inv] = await Promise.all([
        apiGet<{ mentions: any[] }>("/api/candidates/notifications/mentions"),
        apiGet<{ requests: any[] }>("/api/candidates/ownership/requests?scope=inbox"),
        apiGet<{ invitations: any[] }>("/api/candidates/share/invitations?scope=inbox"),
      ]);
      setMentions(m.mentions || []);
      setRequests(r.requests || []);
      setInvitations(inv.invitations || []);
      markAllRead();
    })();
  }, []);

  const mentionItems = useMemo(() => mentions || [], [mentions]);
  const requestItems = useMemo(() => requests || [], [requests]);
  const inviteItems = useMemo(() => invitations || [], [invitations]);
  const seenAt = typeof window !== "undefined" ? (localStorage.getItem("miniats_notif_seen_at") || "") : "";
  const isUnread = (ts?: string) => !!ts && (!seenAt || ts > seenAt);
  const allCount = mentionItems.length + requestItems.length + inviteItems.length;

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 6 }}>Notifications</h2>
            <small>Mentions and ownership request updates.</small>
          </div>
          <button className="btn-outline" style={{ width: "auto" }} onClick={markAllRead}>Mark all as read</button>
        </div>

        <div className="toolbar-actions" style={{ marginTop: 10 }}>
          <button className={tab === "all" ? "btn-outline tab-active" : "btn-outline"} style={{ width: "auto" }} onClick={() => setTab("all")}>All ({allCount})</button>
          <button className={tab === "mentions" ? "btn-outline tab-active" : "btn-outline"} style={{ width: "auto" }} onClick={() => setTab("mentions")}>Mentions ({mentionItems.length})</button>
          <button className={tab === "ownership" ? "btn-outline tab-active" : "btn-outline"} style={{ width: "auto" }} onClick={() => setTab("ownership")}>Ownership ({requestItems.length})</button>
        </div>
      </div>

      {(tab === "all" || tab === "mentions") && (
        <div className="card">
          <h3>Mentions</h3>
          <div className="timeline">
            {mentionItems.map((m) => (
              <div key={m.comment_id} className="timeline-item">
                <div className="timeline-dot" />
                <div>
                  <div className="timeline-title">{isUnread(m.created_at) ? <span className="notif-dot" /> : null} Mentioned in candidate #{m.candidate_id}</div>
                  <div>{m.body}</div>
                  <small>{timeAgo(m.created_at)} · {new Date(m.created_at).toLocaleString()}</small>
                  <div style={{ marginTop: 6 }}>
                    <Link className="chip" href={`/candidates/${m.candidate_id}`}>Open Candidate</Link>
                  </div>
                </div>
              </div>
            ))}
            {!mentionItems.length && <small>No mention notifications yet.</small>}
          </div>
        </div>
      )}


      {(tab === "all") && (
        <div className="card">
          <h3>Share Invitations (Inbox)</h3>
          <div className="timeline">
            {inviteItems.map((inv) => (
              <div key={inv.id} className="timeline-item">
                <div className="timeline-dot" />
                <div>
                  <div className="timeline-title">{isUnread(inv.created_at) ? <span className="notif-dot" /> : null} {inv.from_email} shared candidate #{inv.candidate_id}</div>
                  {inv.reason ? <div>{inv.reason}</div> : null}
                  <small>{timeAgo(inv.created_at)} · {new Date(inv.created_at).toLocaleString()}</small>
                  <div className="toolbar-actions" style={{ marginTop: 6 }}>
                    <button style={{ width: "auto" }} onClick={async () => { const rs = await apiPost<{ clone_candidate_id?: number }>(`/api/candidates/${inv.candidate_id}/share/invitations/${inv.id}/decision`, { decision: "approve" }); const next = inviteItems.filter((x) => x.id !== inv.id); setInvitations(next); if (rs.clone_candidate_id) router.push(`/candidates/${rs.clone_candidate_id}`); }}>Approve & Clone</button>
                    <button className="btn-outline" style={{ width: "auto" }} onClick={async () => { await apiPost(`/api/candidates/${inv.candidate_id}/share/invitations/${inv.id}/decision`, { decision: "reject" }); const next = inviteItems.filter((x) => x.id !== inv.id); setInvitations(next); }}>Reject</button>
                    <Link className="chip" href={`/candidates/${inv.candidate_id}`}>Open Candidate</Link>
                  </div>
                </div>
              </div>
            ))}
            {!inviteItems.length && <small>No share invitations.</small>}
          </div>
        </div>
      )}

      {(tab === "all" || tab === "ownership") && (
        <div className="card">
          <h3>Ownership Requests</h3>
          <div className="timeline">
            {requestItems.map((r) => (
              <div key={r.id} className="timeline-item">
                <div className="timeline-dot" />
                <div>
                  <div className="timeline-title">{isUnread(r.updated_at || r.created_at) ? <span className="notif-dot" /> : null} Candidate #{r.candidate_id} — {r.status}</div>
                  <div>Ownership request is <strong>{r.status}</strong>.</div>
                  <small>{timeAgo(r.updated_at || r.created_at)} · {new Date(r.updated_at || r.created_at).toLocaleString()}</small>
                  <div style={{ marginTop: 6 }}><Link className="chip" href={`/candidates/${r.candidate_id}#req-${r.id}`}>{r.status === "pending" ? "Review Request" : "Open Candidate"}</Link></div>
                </div>
              </div>
            ))}
            {!requestItems.length && <small>No ownership requests yet.</small>}
          </div>
        </div>
      )}
    </div>
  );
}
