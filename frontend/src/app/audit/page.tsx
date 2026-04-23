"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { useMe } from "../../lib/me";

export default function AuditPage() {
  const { me, loading } = useMe();
  const [events, setEvents] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("all");

  useEffect(() => {
    if (me?.role !== "admin") return;
    (async () => {
      const data = await apiGet<{ events: any[] }>("/api/audit?limit=300");
      setEvents(data.events || []);
    })();
  }, [me?.role]);

  const actions = useMemo(() => ["all", ...Array.from(new Set(events.map((e) => e.action)))], [events]);
  const filtered = useMemo(() => {
    return events.filter((e) => {
      const okAction = action === "all" || e.action === action;
      const txt = `${e.timestamp} ${e.actor_email} ${e.action} ${e.target} ${JSON.stringify(e.metadata || {})}`.toLowerCase();
      return okAction && txt.includes(q.toLowerCase());
    });
  }, [events, q, action]);

  if (loading) return <div className="card">Loading...</div>;
  if (me?.role !== "admin") return <div className="card"><h3>No permission</h3><small>Only admin can view audit logs.</small></div>;

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <h2 style={{ marginTop: 0 }}>Audit Log</h2>
            <small>Critical actions across users, candidates, jobs.</small>
          </div>
          <div className="toolbar-actions">
            <input style={{ maxWidth: 260 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search log" />
            <select style={{ width: 220 }} value={action} onChange={(e) => setAction(e.target.value)}>
              {actions.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Metadata</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e, i) => (
              <tr key={i}>
                <td>{e.timestamp}</td>
                <td>{e.actor_email}</td>
                <td>{e.action}</td>
                <td>{e.target}</td>
                <td><small>{JSON.stringify(e.metadata || {})}</small></td>
              </tr>
            ))}
            {!filtered.length && (
              <tr><td colSpan={5}><small>No logs found.</small></td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
