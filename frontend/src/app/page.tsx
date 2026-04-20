import Link from "next/link";
import { apiGet } from "../lib/api";
import type { Analytics, Candidate } from "../components/types";

type SearchParams = {
  keyword?: string;
  skills?: string;
  min_experience?: string;
};

function buildCandidateQuery(searchParams: SearchParams) {
  const qp = new URLSearchParams();

  const keyword = (searchParams.keyword || "").trim();
  const skills = (searchParams.skills || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const minExp = (searchParams.min_experience || "").trim();

  if (keyword) qp.append("keyword", keyword);
  for (const skill of skills) qp.append("skills", skill);
  if (minExp) qp.append("min_experience", minExp);

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

  return (
    <div className="grid">
      <div className="grid grid-2">
        <div className="card">
          <h3>Total Candidates</h3>
          <h1>{analytics.total_candidates}</h1>
        </div>
        <div className="card">
          <h3>Top Skills</h3>
          <ul>
            {analytics.top_skills.slice(0, 5).map((s) => (
              <li key={s.skill}>
                {s.skill} ({s.count})
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h3>Advanced Search</h3>
        <form className="grid grid-3" method="GET">
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
                <td>{c.years_of_experience ?? "-"}</td>
                <td>{(c.skills || []).slice(0, 4).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
