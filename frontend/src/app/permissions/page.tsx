"use client";

import { useMe } from "../../lib/me";

const rows = [
  ["Own candidate", "recruiter", "Yes", "Yes", "Yes", "Yes", "Yes"],
  ["Mentioned candidate (not owner)", "recruiter", "Yes", "No", "No", "No", "Yes"],
  ["Shared invite pending", "recruiter", "Yes", "No", "No", "No", "Yes"],
  ["Approved cloned candidate", "recruiter", "Yes", "Yes", "Yes", "Yes", "Yes"],
  ["Other HR candidate (no mention/share)", "recruiter", "No", "No", "No", "No", "No"],
  ["Own job", "recruiter", "Yes", "Yes", "Yes", "Yes", "-"],
  ["Other HR job", "recruiter", "No", "No", "No", "No", "-"],
  ["Automation rules", "recruiter", "Own only", "Own only", "Own only", "-", "-"],
  ["All entities", "admin", "Yes", "Yes", "Yes", "Yes", "Yes"],
];

export default function PermissionsPage() {
  const { me } = useMe();
  if (me?.role !== "admin") {
    return <div className="card"><h3>Permission Matrix</h3><small>Admin only.</small></div>;
  }

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Permission Matrix</h2>
        <small>Current data-isolation policy (Facebook-style personal ownership).</small>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Entity/Scope</th>
              <th>Role</th>
              <th>View</th>
              <th>Edit</th>
              <th>Delete</th>
              <th>Share/Transfer</th>
              <th>Comment</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => <td key={j}>{c}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
