"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "../lib/api";
import type { Analytics, Candidate, CandidateStatus } from "../components/types";

type SearchParams = {
  keyword?: string;
  skills?: string;
  min_experience?: string;
  status?: CandidateStatus | "";
};

const STATUS_OPTIONS: CandidateStatus[] = ["new", "shortlisted", "interview", "rejected"];

function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function parseQuery(): SearchParams {
  if (typeof window === "undefined") return {};
  const qp = new URLSearchParams(window.location.search);
  return {
    keyword: qp.get("keyword") || "",
    skills: qp.get("skills") || "",
    min_experience: qp.get("min_experience") || "",
    status: (qp.get("status") as CandidateStatus | "") || "",
  };
}

function buildCandidateQuery(searchParams: SearchParams) {
  const qp = new URLSearchParams();

  const keyword = (searchParams.keyword || "").trim();
  const skills = (searchParams.skills || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const minExp = (searchParams.min_experience || "").trim();
  const status = (searchParams.status || "").trim();

  if (keyword) qp.append("keyword", keyword);
  for (const skill of skills) qp.append("skills", skill);
  if (minExp) qp.append("min_experience", minExp);
  if (status) qp.append("status", status);

  const qs = qp.toString();
  return qs ? `/api/candidates?${qs}` : "/api/candidates";
}

function makeCsv(candidates: Candidate[]) {
  const header = ["id", "name", "email", "status", "years_of_experience", "skills"];
  const rows = candidates.map((c) => [
    c.id,
    c.name || "",
    c.email || "",
    c.status || "new",
    c.years_of_experience ?? "",
    (c.skills || []).join("|"),
  ]);
  const lines = [header, ...rows].map((r) =>
    r.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")
  );
  return lines.join("\n");
}

export default function DashboardPage() {
  const [filters, setFilters] = useState<SearchParams>({});
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);

  const loadData = async (nextFilters: SearchParams) => {
    const [candidateData, analyticsData] = await Promise.all([
      apiGet<Candidate[]>(buildCandidateQuery(nextFilters)),
      apiGet<Analytics>("/api/analytics/summary"),
    ]);
    setCandidates(candidateData);
    setAnalytics(analyticsData);
    setSelectedIds([]);
  };

  useEffect(() => {
    const initial = parseQuery();
    setFilters(initial);
    loadData(initial);
  }, []);

  const funnel = useMemo(() => {
    const base = analytics?.status_distribution || [];
    const total = base.reduce((sum, x) => sum + x.count, 0) || 1;
    return base.map((x) => ({ ...x, pct: Math.round((x.count / total) * 100) }));
  }, [analytics]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectAll = () => {
    const shortlistIds = candidates.filter((c) => c.status === "shortlisted").map((c) => c.id);
    setSelectedIds(shortlistIds);
  };

  const bulkSetShortlisted = async () => {
    if (!selectedIds.length) return;
    setBusy(true);
    try {
      await Promise.all(
        selectedIds.map((id) => apiPatch<Candidate>(`/api/candidates/${id}`, { status: "shortlisted" }))
      );
      await loadData(filters);
    } finally {
      setBusy(false);
    }
  };

  const exportSelectedCsv = () => {
    const selected = candidates.filter((c) => selectedIds.includes(c.id));
    const csv = makeCsv(selected);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `shortlist_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const applyFilters = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const nextFilters: SearchParams = {
      keyword: String(fd.get("keyword") || ""),
      skills: String(fd.get("skills") || ""),
      min_experience: String(fd.get("min_experience") || ""),
      status: String(fd.get("status") || "") as CandidateStatus | "",
    };
    setFilters(nextFilters);
    const qs = new URLSearchParams(nextFilters as Record<string, string>);
    window.history.replaceState({}, "", `/?${qs.toString()}`);
    await loadData(nextFilters);
  };

  if (!analytics) return <div className="card">Loading dashboard...</div>;

  return (
    <div className="grid page-enter">
      <div className="grid grid-2">
        <div className="card stat-card">
          <h3>Total Candidates</h3>
          <h1>{analytics.total_candidates}</h1>
          <small>Live pipeline coverage</small>
        </div>
        <div className="card stat-card">
          <h3>Top Skills</h3>
          <div className="chip-wrap" style={{ marginTop: 10 }}>
            {analytics.top_skills.slice(0, 10).map((s) => (
              <span key={s.skill} className="chip">
                {s.skill} • {s.count}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Status Funnel</h3>
        <div className="funnel-grid" style={{ marginTop: 10 }}>
          {funnel.map((item) => (
            <div key={item.status} className="funnel-card">
              <div className="funnel-title">{formatStatus(item.status)}</div>
              <div className="funnel-count">{item.count}</div>
              <div className="mini-bar">
                <div className="mini-bar-fill" style={{ width: `${Math.max(item.pct, 5)}%` }} />
              </div>
              <small>{item.pct}% of total</small>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Advanced Search</h3>
        <form className="grid grid-4" onSubmit={applyFilters}>
          <input name="keyword" defaultValue={filters.keyword || ""} placeholder="Keyword" />
          <input name="skills" defaultValue={filters.skills || ""} placeholder="Skills CSV" />
          <input
            name="min_experience"
            defaultValue={filters.min_experience || ""}
            placeholder="Min experience"
            type="number"
            min={0}
          />
          <select name="status" defaultValue={filters.status || ""}>
            <option value="">All status</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {formatStatus(s)}
              </option>
            ))}
          </select>
          <button type="submit">Apply Filters</button>
        </form>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3>Candidates ({candidates.length})</h3>
          <div className="toolbar-actions">
            <button className="btn-outline" type="button" onClick={selectAll}>
              Select All Shortlisted
            </button>
            <button type="button" onClick={bulkSetShortlisted} disabled={busy || !selectedIds.length}>
              {busy ? "Updating..." : "Bulk Shortlist"}
            </button>
            <button
              className="btn-outline"
              type="button"
              onClick={exportSelectedCsv}
              disabled={!selectedIds.length}
            >
              Export CSV
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th></th>
              <th>Name</th>
              <th>Email</th>
              <th>Status</th>
              <th>Experience</th>
              <th>Skills</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(c.id)}
                    onChange={() => toggleSelect(c.id)}
                  />
                </td>
                <td>
                  <Link href={`/candidates/${c.id}`}>{c.name || "Unknown"}</Link>
                </td>
                <td>{c.email || "-"}</td>
                <td>
                  <span className={`status-badge status-${c.status || "new"}`}>
                    {formatStatus(c.status || "new")}
                  </span>
                </td>
                <td>{c.years_of_experience ?? "-"}</td>
                <td>
                  <div className="chip-wrap">
                    {(c.skills || []).slice(0, 4).map((skill) => (
                      <span key={`${c.id}-${skill}`} className="chip">
                        {skill}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
