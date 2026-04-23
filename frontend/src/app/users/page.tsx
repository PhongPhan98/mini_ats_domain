"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch } from "../../lib/api";
import { notify } from "../../lib/toast";
import { useMe } from "../../lib/me";

type User = { id: number; email: string; full_name: string; role: string; created_at: string };

const ROLES = ["admin", "recruiter", "interviewer", "hiring_manager"];

export default function UsersPage() {
  const { me, loading } = useMe();
  const [users, setUsers] = useState<User[]>([]);
  const [disabled, setDisabled] = useState<number[]>([]);
  const [q, setQ] = useState("");

  const load = async () => {
    const [u, d] = await Promise.all([
      apiGet<User[]>("/api/users"),
      apiGet<{ disabled_user_ids: number[] }>("/api/users/access/disabled"),
    ]);
    setUsers(u);
    setDisabled(d.disabled_user_ids || []);
  };

  useEffect(() => {
    load();
  }, []);

  const setRole = async (id: number, role: string) => {
    await apiPatch(`/api/users/${id}/role`, { role });
    notify("Role updated", "success");
    await load();
  };

  const setDisabledState = async (id: number, value: boolean) => {
    await apiPatch(`/api/users/${id}/disable`, { disabled: value });
    notify(value ? "User disabled" : "User enabled", "success");
    await load();
  };

  if (loading) return <div className="card">Loading...</div>;
  if (me?.role !== "admin") {
    return (
      <div className="card">
        <h3>No permission</h3>
        <small>Only admin can manage users.</small>
      </div>
    );
  }

  const filtered = users.filter((u) => `${u.email} ${u.full_name} ${u.role}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <h2 style={{ marginTop: 0 }}>User Access Management</h2>
            <small>Admin can manage roles and enable/disable HR users.</small>
          </div>
          <input style={{ maxWidth: 300 }} placeholder="Search user" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => {
              const isDisabled = disabled.includes(u.id);
              return (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.full_name}</td>
                  <td>
                    <select value={u.role} onChange={(e) => setRole(u.id, e.target.value)}>
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <span className={`status-badge ${isDisabled ? "status-rejected" : "status-hired"}`}>
                      {isDisabled ? "Disabled" : "Active"}
                    </span>
                  </td>
                  <td>
                    <button className="btn-outline" onClick={() => setDisabledState(u.id, !isDisabled)}>
                      {isDisabled ? "Enable" : "Disable"}
                    </button>
                  </td>
                </tr>
              );
            })}
            {!filtered.length && (
              <tr>
                <td colSpan={5}><small>No users found.</small></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
