export type CandidateStatus = "new" | "shortlisted" | "interview" | "rejected";

export type CandidateFile = {
  id: number;
  file_url: string;
  original_filename: string;
  uploaded_at: string;
};

export type TimelineEvent = {
  type: "created" | "status" | "note" | string;
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
};
