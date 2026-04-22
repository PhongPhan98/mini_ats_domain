"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiUrl } from "../lib/api";
import { useAppLanguage } from "../lib/language";
import type { Analytics, Candidate, CandidateStatus } from "../components/types";

type SearchParams = {
  keyword?: string;
  skills?: string;
  min_experience?: string;
  status?: CandidateStatus | "";
};

type SortKey = "name" | "email" | "phone" | "status" | "years_of_experience" | "created_at";
type SortDir = "asc" | "desc";

const STATUS_OPTIONS: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];

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

export default function DashboardPage() {
  const [filters, setFilters] = useState<SearchParams>({});
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [reportRange, setReportRange] = useState("last_30_days");
  const { t } = useAppLanguage();
  const pageSize = 10;

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

  const sortedCandidates = useMemo(() => {
    const arr = [...candidates];
    arr.sort((a, b) => {
      const av = (a as any)[sortKey];
      const bv = (b as any)[sortKey];
      let cmp = 0;
      if (sortKey === "years_of_experience") cmp = (av ?? -1) - (bv ?? -1);
      else if (sortKey === "created_at") cmp = new Date(av || 0).getTime() - new Date(bv || 0).getTime();
      else cmp = String(av || "").localeCompare(String(bv || ""));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [candidates, sortKey, sortDir]);

  const pagedCandidates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedCandidates.slice(start, start + pageSize);
  }, [sortedCandidates, page]);

  const totalPages = Math.max(1, Math.ceil(sortedCandidates.length / pageSize));

  const funnel = useMemo(() => {
    const base = analytics?.status_distribution || [];
    const total = base.reduce((sum, x) => sum + x.count, 0) || 1;
    return base.map((x) => ({ ...x, pct: Math.round((x.count / total) * 100) }));
  }, [analytics]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
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

  const onSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
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
    await loadData(nextFilters);
  };

  if (!analytics) return <div className="card">Loading dashboard...</div>;

  return (
    <div className="grid page-enter">
      <div className="toolbar">
        <h2>{t("dashboard_title")}</h2>
        <div className="toolbar-actions">
          <select style={{ width: 170 }} value={reportRange} onChange={(e) => setReportRange(e.target.value)}>
            <option value="last_7_days">Last 7 days</option>
            <option value="last_30_days">Last 30 days</option>
            <option value="last_90_days">Last 90 days</option>
            <option value="all_time">All time</option>
          </select>
          <a className="report-btn report-csv" href={apiUrl("/api/reports/candidates.csv")}>{t("report_candidates_csv")}</a>
          <a className="report-btn report-analytics" href={apiUrl("/api/reports/analytics.csv")}>{t("report_analytics_csv")}</a>
          <a className="report-btn report-xlsx" href={apiUrl("/api/reports/reports.xlsx")}>{t("report_xlsx")}</a>
          <a className="report-btn report-pdf" href={apiUrl("/api/reports/report.pdf")}>{t("report_pdf")}</a>
        </div>
      </div>

      <small>Report range preset selected: {reportRange.replaceAll("_", " ")} (export filtering hook prepared for next iteration).</small>

      <div className="grid grid-4">
        <div className="card stat-card"><h3>Total</h3><h1>{analytics.total_candidates}</h1></div>
        <div className="card stat-card"><h3>Hired</h3><h1>{analytics.hired_count}</h1></div>
        <div className="card stat-card"><h3>Avg Time-to-Hire</h3><h1>{analytics.avg_time_to_hire_days}</h1><small>days</small></div>
        <div className="card stat-card"><h3>Top Source</h3><h1>{analytics.source_effectiveness?.[0]?.source || "-"}</h1><small>{analytics.source_effectiveness?.[0]?.share_pct || 0}%</small></div>
      </div>

      <div className="card">
        <h3>Status Funnel</h3>
        <div className="funnel-grid" style={{ marginTop: 10 }}>
          {funnel.map((item) => (
            <div key={item.status} className="funnel-card">
              <div className="funnel-title">{formatStatus(item.status)}</div>
              <div className="funnel-count">{item.count}</div>
              <div className="mini-bar"><div className="mini-bar-fill" style={{ width: `${Math.max(item.pct, 5)}%` }} /></div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-3">
        <div className="card">
          <h3>Pipeline Conversion Rates</h3>
          <ul>{analytics.conversion_rates.map((r) => <li key={r.stage}>{r.stage.replaceAll("_", " ")}: <strong>{r.rate_pct}%</strong></li>)}</ul>
        </div>
        <div className="card">
          <h3>Source Effectiveness</h3>
          <ul>{analytics.source_effectiveness.map((s) => <li key={s.source}>{s.source}: {s.count} ({s.share_pct}%)</li>)}</ul>
        </div>
        <div className="card">
          <h3>Source → Hire Rate</h3>
          <ul>{analytics.source_hire_effectiveness.map((s) => <li key={s.source}>{s.source}: {s.hired}/{s.total} (<strong>{s.hire_rate_pct}%</strong>)</li>)}</ul>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Average Days in Stage</h3>
          <table>
            <thead><tr><th>Stage</th><th>Candidates</th><th>Avg Days</th></tr></thead>
            <tbody>
              {analytics.stage_age_summary.map((s) => (
                <tr key={s.status}>
                  <td>{formatStatus(s.status)}</td>
                  <td>{s.count}</td>
                  <td>{s.avg_days_in_stage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Hiring Trend (Weekly)</h3>
          <table>
            <thead><tr><th>Week Start</th><th>Hired</th></tr></thead>
            <tbody>
              {analytics.hiring_trend.map((w) => (
                <tr key={w.week_start}>
                  <td>{w.week_start}</td>
                  <td>{w.hired_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
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
        <div className="toolbar">
          <h3>Candidates ({sortedCandidates.length})</h3>
          <div className="toolbar-actions">
            <button className="btn-outline" type="button" onClick={() => setSelectedIds(pagedCandidates.map((c) => c.id))}>Select Page</button>
            <button className="btn-outline" type="button" onClick={() => setSelectedIds([])}>Clear</button>
            <button type="button" onClick={() => bulkSetStatus("screening")} disabled={busy || !selectedIds.length}>Move Screening</button>
            <button type="button" onClick={() => bulkSetStatus("interview")} disabled={busy || !selectedIds.length}>Move Interview</button>
            <button type="button" onClick={() => bulkSetStatus("offer")} disabled={busy || !selectedIds.length}>Move Offer</button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th></th>
              <th><button className="btn-outline" onClick={() => onSort("name")}>Name</button></th>
              <th><button className="btn-outline" onClick={() => onSort("email")}>Email</button></th>
              <th><button className="btn-outline" onClick={() => onSort("phone")}>Phone</button></th>
              <th><button className="btn-outline" onClick={() => onSort("status")}>Stage</button></th>
              <th><button className="btn-outline" onClick={() => onSort("years_of_experience")}>Exp</button></th>
              <th><button className="btn-outline" onClick={() => onSort("created_at")}>Created</button></th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedCandidates.map((c) => (
              <tr key={c.id}>
                <td><input type="checkbox" checked={selectedIds.includes(c.id)} onChange={() => toggleSelect(c.id)} /></td>
                <td><Link href={`/candidates/${c.id}`}>{c.name || "Unknown"}</Link></td>
                <td>{c.email || "-"}</td>
                <td>{c.phone || "-"}</td>
                <td>
                  <select value={c.status || "applied"} onChange={(e) => updateOneStatus(c.id, e.target.value as CandidateStatus)}>
                    {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{formatStatus(s)}</option>)}
                  </select>
                </td>
                <td>{c.years_of_experience ?? "-"}</td>
                <td>{c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}</td>
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
