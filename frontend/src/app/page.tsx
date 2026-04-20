import Link from "next/link";
import { apiGet } from "../lib/api";
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

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const [candidates, analytics] = await Promise.all([
    apiGet<Candidate[]>(buildCandidateQuery(params)),
    apiGet<Analytics>("/api/analytics/summary"),
  ]);

  const currentKeyword = params.keyword || "";
  const currentSkills = params.skills || "";
  const currentMinExp = params.min_experience || "";
  const currentStatus = params.status || "";

  return (
    <div className="grid">
      <div className="grid grid-2">
        <div className="card stat-card">
          <h3>Total Candidates</h3>
          <h1>{analytics.total_candidates}</h1>
        </div>
        <div className="card stat-card">
          <h3>Top Skills</h3>
          <div className="chip-wrap" style={{ marginTop: 10 }}>
            {analytics.top_skills.slice(0, 8).map((s) => (
              <span key={s.skill} className="chip">
                {s.skill} • {s.count}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Advanced Search</h3>
        <form className="grid grid-4" method="GET">
          <input
            name="keyword"
            defaultValue={currentKeyword}
            placeholder="Keyword (name, email, summary)"
          />
          <input
            name="skills"
            defaultValue={currentSkills}
            placeholder="Skills (comma-separated)"
          />
          <input
            name="min_experience"
            defaultValue={currentMinExp}
            placeholder="Min years of experience"
            type="number"
            min={0}
          />
          <select name="status" defaultValue={currentStatus}>
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
        <h3>Candidates ({candidates.length})</h3>
        <table>
          <thead>
            <tr>
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
