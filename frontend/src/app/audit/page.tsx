"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { useMe } from "../../lib/me";

export default function AuditPage() {
  const { me, loading } = useMe();
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    if (me?.role !== "admin") return;
    (async () => {
      const data = await apiGet<{ events: any[] }>("/api/audit?limit=300");
      setEvents(data.events || []);
    })();
  }, [me?.role]);

  if (loading) return <div className="card">Loading...</div>;
  if (me?.role !== "admin") return <div className="card"><h3>No permission</h3><small>Only admin can view audit logs.</small></div>;

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Audit Log</h2>
        <small>Critical actions across users, candidates, jobs.</small>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Metadata</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i}>
                <td>{e.timestamp}</td>
                <td>{e.actor_email}</td>
                <td>{e.action}</td>
                <td>{e.target}</td>
                <td><small>{JSON.stringify(e.metadata || {})}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
