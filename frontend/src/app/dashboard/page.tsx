"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Analytics } from "../../components/types";
import { apiGet, apiUrl } from "../../lib/api";
import { formatCandidateStatus } from "../../lib/candidates";
import { useAppLanguage } from "../../lib/language";

export default function DashboardPage() {
  const { t } = useAppLanguage();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Analytics>("/api/analytics/summary")
      .then(setAnalytics)
      .catch(() => setError("Dashboard insights could not be loaded."));
  }, []);

  const funnel = useMemo(() => {
    const distribution = analytics?.status_distribution || [];
    const total = distribution.reduce((sum, item) => sum + item.count, 0) || 1;
    return distribution.map((item) => ({
      ...item,
      percentage: Math.round((item.count / total) * 100),
    }));
  }, [analytics]);

  if (error) {
    return <div className="card empty-state"><strong>Dashboard unavailable</strong><small>{error}</small><button className="btn-secondary" onClick={() => window.location.reload()}>Try again</button></div>;
  }

  if (!analytics) {
    return (
      <div className="grid page-enter">
        <div className="skeleton" style={{ height: 82 }} />
        <div className="grid grid-4">
          {[1, 2, 3, 4].map((item) => <div className="skeleton" style={{ height: 120 }} key={item} />)}
        </div>
        <div className="skeleton" style={{ height: 260 }} />
      </div>
    );
  }

  const topSource = analytics.source_effectiveness[0];

  return (
    <div className="grid page-enter">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Hiring overview</span>
          <h1>{t("dashboard_title")}</h1>
          <p>Monitor recruiting performance and continue your most common tasks.</p>
        </div>
        <div className="toolbar-actions">
          <Link className="btn-secondary" href="/jobs">Manage jobs</Link>
          <Link className="nav-link nav-link-primary" href="/upload">+ Upload CVs</Link>
        </div>
      </div>

      <div className="grid grid-4">
        <div className="card stat-card"><h3>Total candidates</h3><h1>{analytics.total_candidates}</h1><small>Across your talent pool</small></div>
        <div className="card stat-card"><h3>Successful hires</h3><h1>{analytics.hired_count}</h1><small>Completed placements</small></div>
        <div className="card stat-card"><h3>Average time to hire</h3><h1>{analytics.avg_time_to_hire_days}</h1><small>days</small></div>
        <div className="card stat-card"><h3>Top candidate source</h3><h1>{topSource?.source || "—"}</h1><small>{topSource ? `${topSource.share_pct}% of candidates` : "No source data"}</small></div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div><h3 style={{ margin: 0 }}>Hiring pipeline</h3><small>Current candidates by stage</small></div>
          <Link className="chip" href="/pipeline">Open pipeline</Link>
        </div>
        <div className="funnel-grid" style={{ marginTop: 16 }}>
          {funnel.map((item) => (
            <div key={item.status} className="funnel-card">
              <div className="funnel-title">{formatCandidateStatus(item.status)}</div>
              <div className="funnel-count">{item.count}</div>
              <div className="toolbar"><div className="mini-bar"><div className="mini-bar-fill" style={{ width: `${Math.max(item.percentage, 4)}%` }} /></div><small>{item.percentage}%</small></div>
            </div>
          ))}
          {!funnel.length && <div className="empty-state"><strong>No pipeline data</strong><small>Upload a CV to add your first candidate.</small></div>}
        </div>
      </div>

      <div className="grid grid-3">
        <div className="card insight-card">
          <h3>Stage conversion</h3>
          <div className="metric-list">
            {analytics.conversion_rates.map((item) => <div className="metric-row" key={item.stage}><span>{item.stage.replaceAll("_", " ")}</span><strong>{item.rate_pct}%</strong></div>)}
            {!analytics.conversion_rates.length && <small>No conversion data yet.</small>}
          </div>
        </div>
        <div className="card insight-card">
          <h3>Candidate sources</h3>
          <div className="metric-list">
            {analytics.source_effectiveness.slice(0, 6).map((item) => <div className="metric-row" key={item.source}><span>{item.source}</span><strong>{item.count} <small>({item.share_pct}%)</small></strong></div>)}
            {!analytics.source_effectiveness.length && <small>No source data yet.</small>}
          </div>
        </div>
        <div className="card insight-card">
          <h3>Source to hire</h3>
          <div className="metric-list">
            {analytics.source_hire_effectiveness.slice(0, 6).map((item) => <div className="metric-row" key={item.source}><span>{item.source}</span><strong>{item.hire_rate_pct}%</strong></div>)}
            {!analytics.source_hire_effectiveness.length && <small>No hiring data yet.</small>}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Average time in stage</h3>
          <div className="table-scroll"><table><thead><tr><th>Stage</th><th>Candidates</th><th>Average days</th></tr></thead><tbody>
            {analytics.stage_age_summary.map((item) => <tr key={item.status}><td>{formatCandidateStatus(item.status)}</td><td>{item.count}</td><td>{item.avg_days_in_stage}</td></tr>)}
          </tbody></table></div>
        </div>
        <div className="card">
          <h3>Weekly hiring trend</h3>
          <div className="table-scroll"><table><thead><tr><th>Week starting</th><th>Hired</th></tr></thead><tbody>
            {analytics.hiring_trend.map((item) => <tr key={item.week_start}><td>{item.week_start}</td><td>{item.hired_count}</td></tr>)}
          </tbody></table></div>
        </div>
      </div>

      <div className="card toolbar">
        <div><strong>Export reports</strong><small>Download candidate and hiring data for offline analysis.</small></div>
        <div className="toolbar-actions">
          <a className="report-btn report-csv" href={apiUrl("/api/reports/candidates.csv")}>Candidates CSV</a>
          <a className="report-btn report-analytics" href={apiUrl("/api/reports/analytics.csv")}>Analytics CSV</a>
          <a className="report-btn report-xlsx" href={apiUrl("/api/reports/reports.xlsx")}>Excel workbook</a>
          <a className="report-btn report-pdf" href={apiUrl("/api/reports/report.pdf")}>PDF report</a>
        </div>
      </div>
    </div>
  );
}
