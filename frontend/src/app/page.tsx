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

type SortKey = "name" | "email" | "phone" | "status" | "years_of_experience" | "created_at";
type SortDir = "asc" | "desc";

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
  const header = [
    "id",
    "name",
    "email",
    "phone",
    "status",
    "years_of_experience",
    "skills",
    "summary",
    "created_at",
  ];
  const rows = candidates.map((c) => [
    c.id,
    c.name || "",
    c.email || "",
    c.phone || "",
    c.status || "new",
    c.years_of_experience ?? "",
    (c.skills || []).join("|"),
    c.summary || "",
    c.created_at || "",
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

  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>({
    email: true,
    phone: true,
    status: true,
    experience: true,
    skills: true,
    created: true,
  });

  const loadData = async (nextFilters: SearchParams) => {
    const [candidateData, analyticsData] = await Promise.all([
      apiGet<Candidate[]>(buildCandidateQuery(nextFilters)),
      apiGet<Analytics>("/api/analytics/summary"),
    ]);
    setCandidates(candidateData);
    setAnalytics(analyticsData);
    setSelectedIds([]);
    setPage(1);
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

  const sortedCandidates = useMemo(() => {
    const arr = [...candidates];
    arr.sort((a, b) => {
      const av = (a as any)[sortKey];
      const bv = (b as any)[sortKey];
      let cmp = 0;
      if (sortKey === "years_of_experience") {
        cmp = (av ?? -1) - (bv ?? -1);
      } else if (sortKey === "created_at") {
        cmp = new Date(av || 0).getTime() - new Date(bv || 0).getTime();
      } else {
        cmp = String(av || "").localeCompare(String(bv || ""));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [candidates, sortKey, sortDir]);

  const pagedCandidates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedCandidates.slice(start, start + pageSize);
  }, [sortedCandidates, page]);

  const totalPages = Math.max(1, Math.ceil(sortedCandidates.length / pageSize));

  const avgExp = useMemo(() => {
    if (!candidates.length) return 0;
    const values = candidates
      .map((c) => c.years_of_experience)
      .filter((x): x is number => typeof x === "number");
    if (!values.length) return 0;
    return Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(1));
  }, [candidates]);

  const uniqueSkills = useMemo(() => {
    const set = new Set<string>();
    for (const c of candidates) {
      for (const s of c.skills || []) set.add(s.toLowerCase());
    }
    return set.size;
  }, [candidates]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const selectAllVisible = () => setSelectedIds(pagedCandidates.map((c) => c.id));
  const clearSelection = () => setSelectedIds([]);

  const selectAllShortlisted = () => {
    const shortlistIds = candidates.filter((c) => c.status === "shortlisted").map((c) => c.id);
    setSelectedIds(shortlistIds);
  };

  const bulkSetStatus = async (status: CandidateStatus) => {
    if (!selectedIds.length) return;
    setBusy(true);
    try {
      await Promise.all(selectedIds.map((id) => apiPatch<Candidate>(`/api/candidates/${id}`, { status })));
      await loadData(filters);
    } finally {
      setBusy(false);
    }
  };

  const updateOneStatus = async (id: number, status: CandidateStatus) => {
    await apiPatch<Candidate>(`/api/candidates/${id}`, { status });
    setCandidates((prev) => prev.map((c) => (c.id === id ? { ...c, status } : c)));
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

  const onSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  if (!analytics) return <div className="card">Loading dashboard...</div>;

  return (
    <div className="grid page-enter">
      <div className="grid grid-4">
        <div className="card stat-card"><h3>Total Candidates</h3><h1>{analytics.total_candidates}</h1></div>
        <div className="card stat-card"><h3>Avg Experience</h3><h1>{avgExp}</h1></div>
        <div className="card stat-card"><h3>Unique Skills</h3><h1>{uniqueSkills}</h1></div>
        <div className="card stat-card"><h3>Selected</h3><h1>{selectedIds.length}</h1></div>
      </div>

      <div className="card">
        <h3>Status Funnel</h3>
        <div className="funnel-grid" style={{ marginTop: 10 }}>
          {funnel.map((item) => (
            <div key={item.status} className="funnel-card">
              <div className="funnel-title">{formatStatus(item.status)}</div>
              <div className="funnel-count">{item.count}</div>
              <div className="mini-bar"><div className="mini-bar-fill" style={{ width: `${Math.max(item.pct, 5)}%` }} /></div>
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
          <input name="min_experience" defaultValue={filters.min_experience || ""} placeholder="Min experience" type="number" min={0} />
          <select name="status" defaultValue={filters.status || ""}>
            <option value="">All status</option>
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{formatStatus(s)}</option>)}
          </select>
          <button type="submit">Apply Filters</button>
        </form>
      </div>

      <div className="card">
        <h3>Show/Hide Columns</h3>
        <div className="chip-wrap">
          {Object.keys(visibleCols).map((k) => (
            <button key={k} className="btn-outline" style={{ width: "auto" }} onClick={() => setVisibleCols((p) => ({ ...p, [k]: !p[k] }))}>
              {visibleCols[k] ? "✅" : "⬜"} {k}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3>Candidates ({sortedCandidates.length})</h3>
          <div className="toolbar-actions">
            <button className="btn-outline" type="button" onClick={selectAllVisible}>Select Visible</button>
            <button className="btn-outline" type="button" onClick={selectAllShortlisted}>Select Shortlisted</button>
            <button className="btn-outline" type="button" onClick={clearSelection}>Clear</button>
            <button type="button" onClick={() => bulkSetStatus("shortlisted")} disabled={busy || !selectedIds.length}>Shortlist</button>
            <button type="button" onClick={() => bulkSetStatus("interview")} disabled={busy || !selectedIds.length}>Interview</button>
            <button type="button" onClick={() => bulkSetStatus("rejected")} disabled={busy || !selectedIds.length}>Reject</button>
            <button className="btn-outline" type="button" onClick={exportSelectedCsv} disabled={!selectedIds.length}>Export CSV</button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th></th>
              <th><button className="btn-outline" onClick={() => onSort("name")}>Name</button></th>
              {visibleCols.email && <th><button className="btn-outline" onClick={() => onSort("email")}>Email</button></th>}
              {visibleCols.phone && <th><button className="btn-outline" onClick={() => onSort("phone")}>Phone</button></th>}
              {visibleCols.status && <th><button className="btn-outline" onClick={() => onSort("status")}>Status</button></th>}
              {visibleCols.experience && <th><button className="btn-outline" onClick={() => onSort("years_of_experience")}>Experience</button></th>}
              {visibleCols.skills && <th>Skills</th>}
              {visibleCols.created && <th><button className="btn-outline" onClick={() => onSort("created_at")}>Created</button></th>}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedCandidates.map((c) => (
              <tr key={c.id}>
                <td><input type="checkbox" checked={selectedIds.includes(c.id)} onChange={() => toggleSelect(c.id)} /></td>
                <td><Link href={`/candidates/${c.id}`}>{c.name || "Unknown"}</Link></td>
                {visibleCols.email && <td>{c.email || "-"}</td>}
                {visibleCols.phone && <td>{c.phone || "-"}</td>}
                {visibleCols.status && (
                  <td>
                    <select value={c.status || "new"} onChange={(e) => updateOneStatus(c.id, e.target.value as CandidateStatus)}>
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{formatStatus(s)}</option>)}
                    </select>
                  </td>
                )}
                {visibleCols.experience && <td>{c.years_of_experience ?? "-"}</td>}
                {visibleCols.skills && <td><div className="chip-wrap">{(c.skills || []).slice(0, 5).map((skill) => <span key={`${c.id}-${skill}`} className="chip">{skill}</span>)}</div></td>}
                {visibleCols.created && <td>{c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}</td>}
                <td><Link href={`/candidates/${c.id}`} className="chip">Edit</Link></td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="toolbar" style={{ marginTop: 12 }}>
          <small>Page {page} / {totalPages}</small>
          <div className="toolbar-actions">
            <button className="btn-outline" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
            <button className="btn-outline" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
