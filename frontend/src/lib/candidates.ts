import type { Candidate, CandidateStatus } from "../components/types";

export type CandidateSearchParams = {
  keyword?: string;
  skills?: string;
  min_experience?: string;
  status?: CandidateStatus | "";
};

export type CandidateSortKey =
  | "name"
  | "email"
  | "phone"
  | "status"
  | "years_of_experience"
  | "created_at";

export const CANDIDATE_STATUSES: CandidateStatus[] = [
  "applied",
  "screening",
  "interview",
  "offer",
  "hired",
  "rejected",
];

export function formatCandidateStatus(status: string) {
  return status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
}

export function readCandidateSearchParams(): CandidateSearchParams {
  if (typeof window === "undefined") return {};
  const query = new URLSearchParams(window.location.search);
  return {
    keyword: query.get("keyword") || "",
    skills: query.get("skills") || "",
    min_experience: query.get("min_experience") || "",
    status: (query.get("status") as CandidateStatus | "") || "",
  };
}

export function buildCandidateQuery(filters: CandidateSearchParams) {
  const query = new URLSearchParams();
  const keyword = (filters.keyword || "").trim();
  const minExperience = (filters.min_experience || "").trim();

  if (keyword) query.set("keyword", keyword);
  for (const skill of (filters.skills || "").split(",").map((value) => value.trim()).filter(Boolean)) {
    query.append("skills", skill);
  }
  if (minExperience) query.set("min_experience", minExperience);
  if (filters.status) query.set("status", filters.status);

  return query;
}

export function canManageCandidate(
  candidate: Candidate,
  user?: { id?: number; email?: string } | null,
) {
  const ownerEmail = String(candidate.parsed_json?.owner_email || "").toLowerCase();
  const ownerUserId = Number(candidate.parsed_json?.owner_user_id || 0);
  const userEmail = String(user?.email || "").toLowerCase();
  const userId = Number(user?.id || 0);
  return (
    (!!ownerEmail && !!userEmail && ownerEmail === userEmail) ||
    (!!ownerUserId && !!userId && ownerUserId === userId)
  );
}
