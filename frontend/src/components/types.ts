export type CandidateStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "hired"
  | "rejected";

export type CandidateFile = {
  id: number;
  file_url: string;
  original_filename: string;
  uploaded_at: string;
};

export type TimelineEvent = {
  type: "created" | "status" | "note" | "automation" | string;
  value: string;
  timestamp: string;
};

export type Candidate = {
  id: number;
  name?: string;
  email?: string;
  phone?: string;
  status: CandidateStatus;
  skills: string[];
  years_of_experience?: number;
  education: string[];
  previous_companies: string[];
  summary?: string;
  parsed_json: {
    linkedin_url?: string;
    github_url?: string;
    location?: string;
    current_title?: string;
    certifications?: string[];
    languages?: string[];
    projects?: string[];
    timeline?: TimelineEvent[];
    [key: string]: any;
  };
  files: CandidateFile[];
  created_at: string;
};

export type Analytics = {
  total_candidates: number;
  top_skills: { skill: string; count: number }[];
  experience_distribution: { range: string; count: number }[];
  status_distribution: { status: CandidateStatus; count: number }[];
  source_effectiveness: { source: string; count: number; share_pct: number }[];
  conversion_rates: { stage: string; rate_pct: number }[];
  avg_time_to_hire_days: number;
  hired_count: number;
  stage_age_summary: { status: CandidateStatus; count: number; avg_days_in_stage: number }[];
  source_hire_effectiveness: { source: string; total: number; hired: number; hire_rate_pct: number }[];
  hiring_trend: { week_start: string; hired_count: number }[];
};
