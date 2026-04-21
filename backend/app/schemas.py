from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


CandidateStatus = Literal["applied", "screening", "interview", "offer", "hired", "rejected"]
UserRole = Literal["admin", "recruiter", "interviewer", "hiring_manager"]


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateFileOut(BaseModel):
    id: int
    file_url: str
    original_filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class CandidateCommentCreate(BaseModel):
    body: str


class CandidateCommentOut(BaseModel):
    id: int
    candidate_id: int
    author_user_id: int
    body: str
    mentions: list[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewScorecardCreate(BaseModel):
    interview_stage: str = "interview"
    criteria_scores: dict[str, int] = Field(default_factory=dict)
    overall_score: int | None = None
    recommendation: str | None = None
    summary: str | None = None


class InterviewScorecardOut(BaseModel):
    id: int
    candidate_id: int
    interviewer_user_id: int
    interview_stage: str
    criteria_scores: dict[str, int] = Field(default_factory=dict)
    overall_score: int | None = None
    recommendation: str | None = None
    summary: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewScheduleCreate(BaseModel):
    interviewer_email: str
    scheduled_at: datetime
    duration_minutes: int = 60
    meeting_link: str | None = None
    notes: str | None = None


class InterviewScheduleOut(BaseModel):
    id: int
    candidate_id: int
    organizer_user_id: int
    interviewer_email: str
    scheduled_at: datetime
    duration_minutes: int
    meeting_link: str | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: int
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: CandidateStatus = "applied"
    skills: list[str] = Field(default_factory=list)
    years_of_experience: int | None = None
    education: list[str] = Field(default_factory=list)
    previous_companies: list[str] = Field(default_factory=list)
    summary: str | None = None
    parsed_json: dict[str, Any] = Field(default_factory=dict)
    files: list[CandidateFileOut] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: CandidateStatus | None = None
    skills: list[str] | None = None
    years_of_experience: int | None = None
    education: list[str] | None = None
    previous_companies: list[str] | None = None
    summary: str | None = None
    notes: str | None = None


class CandidateSearchQuery(BaseModel):
    skills: list[str] = Field(default_factory=list)
    min_experience: int | None = None
    keyword: str | None = None
    status: CandidateStatus | None = None


class JobCreate(BaseModel):
    title: str
    requirements: str


class JobOut(BaseModel):
    id: int
    title: str
    requirements: str
    created_at: datetime

    class Config:
        from_attributes = True


class MatchItem(BaseModel):
    candidate_id: int
    candidate_name: str | None = None
    match_score: int
    explanation: str


class MatchResponse(BaseModel):
    job_id: int
    job_title: str
    results: list[MatchItem]


class AnalyticsSummary(BaseModel):
    top_skills: list[dict]
    experience_distribution: list[dict]
    status_distribution: list[dict]
    total_candidates: int
