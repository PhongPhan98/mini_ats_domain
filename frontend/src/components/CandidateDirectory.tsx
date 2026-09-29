"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../lib/api";
import {
  buildCandidateQuery,
  canManageCandidate,
  CANDIDATE_STATUSES,
  CandidateSearchParams,
  CandidateSortKey,
  formatCandidateStatus,
  readCandidateSearchParams,
} from "../lib/candidates";
import { useMe } from "../lib/me";
import { notify } from "../lib/toast";
import type { Candidate, CandidateStatus } from "./types";

const PAGE_SIZE = 12;

export default function CandidateDirectory() {
  const { me } = useMe();
  const [filters, setFilters] = useState<CandidateSearchParams>({});
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [sortKey, setSortKey] = useState<CandidateSortKey>("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [showTrash, setShowTrash] = useState(false);
  const [compact, setCompact] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadCandidates = async (nextFilters: CandidateSearchParams, trash = showTrash) => {
    setLoading(true);
    setError("");
    try {
      const query = buildCandidateQuery(nextFilters);
      query.set("include_deleted", String(trash));
      const data = await apiGet<Candidate[]>(`/api/candidates?${query.toString()}`);
      setCandidates(data);
      setSelectedIds([]);
      setPage(1);
    } catch {
      setError("Candidates could not be loaded. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initial = readCandidateSearchParams();
    setFilters(initial);
    loadCandidates(initial, showTrash);
  }, [showTrash]);

  const sortedCandidates = useMemo(() => {
    return [...candidates].sort((left, right) => {
      const leftValue = left[sortKey];
      const rightValue = right[sortKey];
      let comparison: number;
      if (sortKey === "years_of_experience") {
        comparison = Number(leftValue ?? -1) - Number(rightValue ?? -1);
      } else if (sortKey === "created_at") {
        comparison = new Date(String(leftValue || 0)).getTime() - new Date(String(rightValue || 0)).getTime();
      } else {
        comparison = String(leftValue || "").localeCompare(String(rightValue || ""));
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [candidates, sortDirection, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sortedCandidates.length / PAGE_SIZE));
  const visibleCandidates = sortedCandidates.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const manageableVisibleIds = visibleCandidates
    .filter((candidate) => canManageCandidate(candidate, me))
    .map((candidate) => candidate.id);

  const sortBy = (key: CandidateSortKey) => {
    if (key === sortKey) setSortDirection((current) => current === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const sortLabel = (label: string, key: CandidateSortKey) =>
    `${label}${sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : ""}`;

  const toggleCandidate = (id: number) => {
    setSelectedIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  };

  const applyFilters = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nextFilters: CandidateSearchParams = {
      keyword: String(form.get("keyword") || ""),
      skills: String(form.get("skills") || ""),
      min_experience: String(form.get("min_experience") || ""),
      status: String(form.get("status") || "") as CandidateStatus | "",
    };
    setFilters(nextFilters);
    const query = buildCandidateQuery(nextFilters).toString();
    window.history.replaceState({}, "", query ? `/candidates?${query}` : "/candidates");
    await loadCandidates(nextFilters);
  };

  const removeCandidate = async (id: number) => {
    await apiDelete(`/api/candidates/${id}`);
    await loadCandidates(filters);
    notify("Candidate moved to trash", "success");
  };

  const restoreCandidate = async (id: number) => {
    await apiPost(`/api/candidates/${id}/restore`, {});
    await loadCandidates(filters);
    notify("Candidate restored", "success");
  };

  return (
    <div className="grid page-enter">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Talent database</span>
          <h1>Candidates</h1>
          <p>Search profiles and keep your active talent pool organized. Update job stages in Pipeline.</p>
        </div>
        <Link className="nav-link nav-link-primary" href="/upload">+ Upload CVs</Link>
      </div>

      <form className="card candidate-filters" onSubmit={applyFilters}>
        <div className="grid grid-4">
          <input name="keyword" defaultValue={filters.keyword || ""} placeholder="Search name, email or title" />
          <input name="skills" defaultValue={filters.skills || ""} placeholder="Skills, separated by commas" />
          <input name="min_experience" defaultValue={filters.min_experience || ""} placeholder="Minimum experience" type="number" min={0} />
          <select name="status" defaultValue={filters.status || ""}>
            <option value="">All stages</option>
            {CANDIDATE_STATUSES.map((status) => <option key={status} value={status}>{formatCandidateStatus(status)}</option>)}
          </select>
        </div>
        <div className="toolbar candidate-filter-actions">
          <small>Use multiple skills to narrow results.</small>
          <button type="submit" className="btn-large">Search candidates</button>
        </div>
      </form>

      <div className="card">
        <div className="toolbar sticky-toolbar">
          <div>
            <h3 style={{ margin: 0 }}>{showTrash ? "Deleted candidates" : "Active candidates"} ({sortedCandidates.length})</h3>
            <small>{selectedIds.length ? `${selectedIds.length} selected` : "Select candidates to update them together."}</small>
          </div>
          <div className="toolbar-actions">
            <button className="btn-outline" type="button" onClick={() => setCompact((value) => !value)}>{compact ? "Comfortable view" : "Compact view"}</button>
            <button className="btn-outline" type="button" onClick={() => setShowTrash((value) => !value)}>{showTrash ? "Back to active" : "Trash"}</button>
            {!showTrash && <>
              <button className="btn-outline" type="button" onClick={() => setSelectedIds(manageableVisibleIds)}>Select page</button>
              <button className="btn-outline" type="button" onClick={() => setSelectedIds([])} disabled={!selectedIds.length}>Clear</button>
            </>}
          </div>
        </div>

        {error && <div className="inline-alert">{error}</div>}
        {loading ? <div className="candidate-loading"><div className="spinner" /><span>Loading candidates...</span></div> : (
          <div className="candidate-table-scroll">
            <table className={`candidate-table ${compact ? "candidate-table-compact" : ""}`}>
              <thead>
                <tr>
                  <th aria-label="Select" />
                  <th><button className="btn-outline" onClick={() => sortBy("name")}>{sortLabel("Name", "name")}</button></th>
                  <th><button className="btn-outline" onClick={() => sortBy("email")}>{sortLabel("Email", "email")}</button></th>
                  <th><button className="btn-outline" onClick={() => sortBy("phone")}>{sortLabel("Phone", "phone")}</button></th>
                  <th><button className="btn-outline" onClick={() => sortBy("status")}>{sortLabel("Stage", "status")}</button></th>
                  <th><button className="btn-outline" onClick={() => sortBy("years_of_experience")}>{sortLabel("Experience", "years_of_experience")}</button></th>
                  <th><button className="btn-outline" onClick={() => sortBy("created_at")}>{sortLabel("Added", "created_at")}</button></th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {!visibleCandidates.length && <tr><td colSpan={8}><div className="empty-state"><strong>No candidates found</strong><small>Change the filters or upload a new CV.</small><Link className="btn-secondary" href="/upload">Upload CV</Link></div></td></tr>}
                {visibleCandidates.map((candidate) => {
                  const manageable = canManageCandidate(candidate, me);
                  return (
                    <tr key={candidate.id}>
                      <td><input type="checkbox" aria-label={`Select ${candidate.name || "candidate"}`} disabled={!manageable || showTrash} checked={selectedIds.includes(candidate.id)} onChange={() => toggleCandidate(candidate.id)} /></td>
                      <td><Link className="candidate-name-link" href={`/candidates/${candidate.id}`}>{candidate.name || "Unknown candidate"}</Link></td>
                      <td>{candidate.email || "—"}</td>
                      <td>{candidate.phone || "—"}</td>
                      <td>
                        <span className={`status-badge status-${candidate.status || "applied"}`}>{formatCandidateStatus(candidate.status || "applied")}</span>
                      </td>
                      <td>{candidate.years_of_experience == null ? "—" : `${candidate.years_of_experience} years`}</td>
                      <td>{candidate.created_at ? new Date(candidate.created_at).toLocaleDateString() : "—"}</td>
                      <td className="candidate-actions"><div className="toolbar-actions">
                        <Link href={`/candidates/${candidate.id}`} className="chip">View</Link>
                        {showTrash ? <button className="btn-outline" type="button" disabled={!manageable} onClick={() => restoreCandidate(candidate.id)}>Restore</button> : manageable ? <button className="btn-outline danger-action" type="button" onClick={() => removeCandidate(candidate.id)}>Delete</button> : <span className="chip">View only</span>}
                      </div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="toolbar table-pagination">
          <small>Page {page} of {totalPages} · {sortedCandidates.length} candidates</small>
          <div className="toolbar-actions">
            <button className="btn-outline" type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button>
            <button className="btn-outline" type="button" disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
