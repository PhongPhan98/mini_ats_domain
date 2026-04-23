"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../../../lib/api";
import { useAppLanguage } from "../../../lib/language";
import { useMe } from "../../../lib/me";
import { notify } from "../../../lib/toast";
import type { Candidate, CandidateStatus, TimelineEvent } from "../../../components/types";

type CandidateForm = {
  name: string;
  email: string;
  phone: string;
  status: CandidateStatus;
  years_of_experience: string;
  skills_text: string;
  education_text: string;
  previous_companies_text: string;
  summary: string;
  note: string;
};

type CandidateComment = {
  id: number;
  candidate_id: number;
  author_user_id: number;
  author_name?: string;
  body: string;
  mentions: string[];
  created_at: string;
};

type InterviewScorecard = {
  id: number;
  candidate_id: number;
  interviewer_user_id: number;
  interview_stage: string;
  criteria_scores: Record<string, number>;
  overall_score?: number;
  recommendation?: string;
  summary?: string;
  created_at: string;
};

type InterviewSchedule = {
  id: number;
  candidate_id: number;
  organizer_user_id: number;
  interviewer_email: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_link?: string;
  notes?: string;
  created_at: string;
};

const STATUS_OPTIONS: CandidateStatus[] = ["applied", "screening", "interview", "offer", "hired", "rejected"];

function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function toForm(c: Candidate): CandidateForm {
  return {
    name: c.name || "",
    email: c.email || "",
    phone: c.phone || "",
    status: c.status || "applied",
    years_of_experience: c.years_of_experience?.toString() || "",
    skills_text: (c.skills || []).join(", "),
    education_text: (c.education || []).join("\n"),
    previous_companies_text: (c.previous_companies || []).join("\n"),
    summary: c.summary || "",
    note: "",
  };
}

function normalizeCommaList(text: string): string[] {
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

function normalizeLineList(text: string): string[] {
  return text.split("\n").map((s) => s.trim()).filter(Boolean);
}

function timelineOf(candidate: Candidate): TimelineEvent[] {
  return (candidate.parsed_json?.timeline || []).slice().reverse();
}

function formatTimelineTitle(lang: string, evType: string) {
  const vi = lang === "vi";
  const t = String(evType || "").toLowerCase();
  if (t === "created") return vi ? "Khởi tạo" : "Created";
  if (t === "status") return vi ? "Trạng thái" : "Status";
  if (t === "automation") return vi ? "Tự động hoá" : "Automation";
  if (t === "comment") return vi ? "Bình luận" : "Comment";
  if (t === "mention") return vi ? "Nhắc thẻ" : "Mention";
  if (t === "share") return vi ? "Chia sẻ" : "Sharing";
  if (t === "note") return vi ? "Ghi chú" : "Note";
  return vi ? "Sự kiện" : "Event";
}

function formatTimelineTime(lang: string, ts?: string) {
  if (!ts) return "-";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString(lang === "vi" ? "vi-VN" : "en-US");
}

function formatTimelineEvent(lang: string, ev: TimelineEvent) {
  const vi = lang === "vi";
  const type = String(ev.type || "").toLowerCase();
  const val = String(ev.value || "");

  if (type === "created") return vi ? "Tạo hồ sơ ứng viên" : "Candidate profile created";
  if (type === "status") {
    return vi ? `Chuyển trạng thái sang: ${val}` : `Status changed to: ${val}`;
  }
  if (type === "automation") {
    const stage = val.split(":").pop() || val;
    return vi ? `Tự động hoá đã gửi thông báo cho vòng ${stage}` : `Automation sent notification for stage ${stage}`;
  }
  if (type === "comment") return vi ? `Bình luận: ${val}` : `Comment: ${val}`;
  if (type === "mention") return vi ? `Đã nhắc thẻ: ${val}` : `Mentioned: ${val}`;
  if (type === "note") {
    if (val.startsWith("auto_action:notify_on_stage_change:")) {
      const stage = val.split(":").pop() || val;
      return vi ? `Tự động gửi thông báo khi ứng viên vào vòng ${stage}` : `Auto notification sent when candidate entered ${stage} stage`;
    }
    if (val.startsWith("status_changed:")) {
      const st = val.split(":").pop() || val;
      return vi ? `Cập nhật trạng thái: ${st}` : `Status updated: ${st}`;
    }
    if (val === "candidate_soft_deleted") return vi ? "Ứng viên được chuyển vào Thùng rác" : "Candidate moved to Trash";
    if (val === "candidate_restored") return vi ? "Ứng viên được khôi phục" : "Candidate restored";
    return vi ? `Ghi chú: ${val}` : `Note: ${val}`;
  }

  if (type === "share") {
    if (val.startsWith("shared_with:")) return vi ? `Đã chia sẻ cho ${val.replace("shared_with:", "")}` : `Shared with ${val.replace("shared_with:", "")}`;
    if (val.startsWith("unshared_with:")) return vi ? `Đã huỷ chia sẻ với ${val.replace("unshared_with:", "")}` : `Unshared with ${val.replace("unshared_with:", "")}`;
  }
  return val;
}

export default function CandidateDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [form, setForm] = useState<CandidateForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [candidateId, setCandidateId] = useState<string>("");
  const [comments, setComments] = useState<CandidateComment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [scorecards, setScorecards] = useState<InterviewScorecard[]>([]);
  const [scoreOverall, setScoreOverall] = useState("");
  const [scoreRecommendation, setScoreRecommendation] = useState("strong_yes");
  const [scoreSummary, setScoreSummary] = useState("");
  const [scoreTech, setScoreTech] = useState("3");
  const [scoreComm, setScoreComm] = useState("3");
  const [scoreProblem, setScoreProblem] = useState("3");
  const [schedules, setSchedules] = useState<InterviewSchedule[]>([]);
  const [schedInterviewer, setSchedInterviewer] = useState("");
  const [schedAt, setSchedAt] = useState("");
  const [schedDuration, setSchedDuration] = useState("60");
  const [schedLink, setSchedLink] = useState("");
  const [schedNotes, setSchedNotes] = useState("");
  const [shareEmail, setShareEmail] = useState("");
  const [shareReason, setShareReason] = useState("");
  const [ownershipReason, setOwnershipReason] = useState("");
  const [selectedFileUrl, setSelectedFileUrl] = useState("");
  const { t, lang } = useAppLanguage();
  const { me } = useMe();

  const loadComments = async (id: string) => {
    const data = await apiGet<CandidateComment[]>(`/api/candidates/${id}/comments`);
    setComments(data);
  };

  const loadScorecards = async (id: string) => {
    const data = await apiGet<InterviewScorecard[]>(`/api/candidates/${id}/scorecards`);
    setScorecards(data);
  };

  const loadSchedules = async (id: string) => {
    const data = await apiGet<InterviewSchedule[]>(`/api/candidates/${id}/schedules`);
    setSchedules(data);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resolved = await params;
        if (cancelled) return;
        setCandidateId(resolved.id);
        const data = await apiGet<Candidate>(`/api/candidates/${resolved.id}`);
        if (cancelled) return;
        setCandidate(data);
        setForm(toForm(data));
        setSelectedFileUrl(data.files?.[0]?.file_url || "");
        await Promise.all([loadComments(resolved.id), loadScorecards(resolved.id), loadSchedules(resolved.id)]);
      } catch (e: any) {
        if (!cancelled) setError(e.message || "Failed to load candidate");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params]);

  const canSave = useMemo(() => !!form && !saving, [form, saving]);
  const meEmail = String(me?.email || "").toLowerCase();
  const ownerEmail = String((candidate?.parsed_json as any)?.owner_email || "").toLowerCase();
  const ownerUserId = Number((candidate?.parsed_json as any)?.owner_user_id || 0);
  const isOwner = (!!meEmail && !!ownerEmail && ownerEmail === meEmail) || (!!me?.id && ownerUserId > 0 && Number(me.id) === ownerUserId);
  const isViewOnly = !isOwner;
  const pendingOwnershipRequests = (((candidate?.parsed_json as any)?.ownership_requests || []) as any[]).filter((r) => r.status === "pending" && String(r.to_email || "").toLowerCase() === ownerEmail);
  const updateField = (key: keyof CandidateForm, value: string) =>
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));

  const onSave = async () => {
    if (!form || !candidateId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        name: form.name || null,
        email: form.email || null,
        phone: form.phone || null,
        status: form.status,
        years_of_experience: form.years_of_experience ? Number(form.years_of_experience) : null,
        skills: normalizeCommaList(form.skills_text),
        education: normalizeLineList(form.education_text),
        previous_companies: normalizeLineList(form.previous_companies_text),
        summary: form.summary || null,
        notes: form.note || null,
      };
      const updated = await apiPatch<Candidate>(`/api/candidates/${candidateId}`, payload);
      setCandidate(updated);
      const next = toForm(updated);
      next.note = "";
      setForm(next);
      setMessage(t("update_success"));
      notify(t("update_success"), "success");
    } catch (e: any) {
      setError(e.message || t("save_failed"));
      notify(t("save_failed"), "error");
    } finally {
      setSaving(false);
    }
  };

  const onAddComment = async () => {
    const body = newComment.trim();
    if (!body || !candidateId) { notify(t("missing_required_fields"), "error"); return; }
    await apiPost(`/api/candidates/${candidateId}/comments`, { body });
    setNewComment("");
    await loadComments(candidateId);
    notify(t("update_success"), "success");
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
  };

  const onAddScorecard = async () => {
    if (!candidateId) return;
    await apiPost(`/api/candidates/${candidateId}/scorecards`, {
      interview_stage: "interview",
      criteria_scores: {
        technical: Number(scoreTech),
        communication: Number(scoreComm),
        problem_solving: Number(scoreProblem),
      },
      overall_score: scoreOverall ? Number(scoreOverall) : null,
      recommendation: scoreRecommendation,
      summary: scoreSummary || null,
    });
    setScoreSummary("");
    setScoreOverall("");
    await loadScorecards(candidateId);
    notify(t("update_success"), "success");
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
  };

  const onShareCandidate = async () => {
    if (!candidateId || !shareEmail.trim()) { notify(t("missing_required_fields"), "error"); return; }
    await apiPost(`/api/candidates/${candidateId}/share`, { email: shareEmail.trim() });
    setShareEmail("");
      setShareReason("");
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
    notify(t("update_success"), "success");
  };

  const onUnshareCandidate = async (email: string) => {
    if (!candidateId) return;
    await apiPost(`/api/candidates/${candidateId}/unshare`, { email });
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
    notify(t("update_success"), "success");
  };

  const onOwnershipDecision = async (requestId: string, decision: "approve" | "reject") => {
    if (!candidateId) return;
    await apiPost(`/api/candidates/${candidateId}/ownership/requests/${requestId}/decision`, { decision });
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
    notify(decision === "approve" ? "Request approved" : "Request rejected", "success");
  };

  const onScheduleInterview = async () => {
    if (!candidateId || !schedInterviewer || !schedAt) { notify(t("missing_required_fields"), "error"); return; }
    await apiPost(`/api/candidates/${candidateId}/schedules`, {
      interviewer_email: schedInterviewer,
      scheduled_at: new Date(schedAt).toISOString(),
      duration_minutes: Number(schedDuration || 60),
      meeting_link: schedLink || null,
      notes: schedNotes || null,
    });
    setSchedNotes("");
    setSchedLink("");
    await loadSchedules(candidateId);
    notify(t("schedule_success"), "success");
    const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
    setCandidate(updated);
  };

  const onDeleteFile = async (fileId: number) => {
    if (!candidateId) return;
    try {
      await apiDelete(`/api/candidates/${candidateId}/files/${fileId}`);
      const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`);
      setCandidate(updated);
      setSelectedFileUrl(updated.files?.[0]?.file_url || "");
      notify(t("update_success"), "success");
    } catch {
      notify(t("save_failed"), "error");
    }
  };

  if (loading) return <div className="card">{t("loading_candidate")}</div>;
  if (error && !candidate)
    return (
      <div className="card">
        <p style={{ color: "red" }}>{error}</p>
        <Link href="/">Back</Link>
      </div>
    );
  if (!form || !candidate)
    return (
      <div className="card">
        <p>{t("candidate_not_found")}</p>
        <Link href="/">Back</Link>
      </div>
    );

  return (
    <div className="grid page-enter">
      <div className="card">
        <div className="toolbar">
          <div>
            <Link href="/">← {t("back")}</Link>
            <h2 style={{ margin: "10px 0 0" }}>{candidate.name || t("candidate_detail")}</h2>
            <small>{candidate.email || t("no_email")}</small>
          </div>
          <span className={`status-badge status-${candidate.status || "applied"}`}>
            {formatStatus(candidate.status || "applied")}
          </span>
          {!isOwner ? <div className="toolbar-actions"><input style={{ maxWidth: 260 }} value={ownershipReason} onChange={(e) => setOwnershipReason(e.target.value)} placeholder="Reason to request ownership" /> <button className="btn-outline" style={{ width: "auto" }} onClick={async () => { await apiPost(`/api/candidates/${candidateId}/ownership/request`, { reason: ownershipReason }); notify("Ownership request sent", "success"); const updated = await apiGet<Candidate>(`/api/candidates/${candidateId}`); setCandidate(updated); }} disabled={(((candidate?.parsed_json as any)?.ownership_requests || []) as any[]).some((r) => String(r.from_email||"").toLowerCase()===meEmail && r.status==="pending")}>Request ownership</button></div> : null}
        </div>
      </div>

{!isViewOnly ? <div className="card">
        <div className="toolbar">
          <h3 style={{ margin: 0 }}>Original CV Files</h3>
          <small>{candidate.files?.length || 0} file(s)</small>
        </div>
        <div className="split-grid" style={{ marginTop: 10 }}>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="grid">
              {(candidate.files || []).map((f) => (
                <div key={f.id} className="toolbar" style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 8 }}>
                  <a href={f.file_url} target="_blank">{f.original_filename}</a>
                  <div className="toolbar-actions">
                    <button className="btn-outline" style={{ width: "auto" }} onClick={() => setSelectedFileUrl(f.file_url)}>View</button>
                    {isOwner ? <button className="btn-outline" style={{ width: "auto" }} onClick={() => onDeleteFile(f.id)}>Delete</button> : null}
                  </div>
                </div>
              ))}
              {!candidate.files?.length && <small>No CV files</small>}
            </div>
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            {selectedFileUrl ? (
              <iframe title="cv-preview" src={selectedFileUrl} style={{ width: "100%", height: 560, border: "1px solid var(--border)", borderRadius: 10 }} />
            ) : (
              <small>Select a file to preview</small>
            )}
          </div>
        </div>
      </div> : null}

      <div className="card">
        <h3>{t("profile_information")}</h3>
        <div className="grid grid-2">
          <div>
            <label>{t("name")}</label>
            <input value={form.name} onChange={(e) => updateField("name", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
          </div>
          <div>
            <label>{t("email")}</label>
            <input value={form.email} onChange={(e) => updateField("email", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
          </div>
          <div>
            <label>{t("phone")}</label>
            <input value={form.phone} onChange={(e) => updateField("phone", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
          </div>
          <div>
            <label>{t("stage_label")}</label>
            <select value={form.status} onChange={(e) => updateField("status", e.target.value)} disabled={isViewOnly}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {formatStatus(s)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>{t("years_experience")}</label>
            <input
              type="number"
              min={0}
              value={form.years_of_experience}
              onChange={(e) => updateField("years_of_experience", e.target.value)}
             readOnly={isViewOnly} disabled={isViewOnly} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <label>{t("skills_csv")}</label>
          <input value={form.skills_text} onChange={(e) => updateField("skills_text", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label>{t("education")}</label>
          <textarea rows={4} value={form.education_text} onChange={(e) => updateField("education_text", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label>{t("previous_companies")}</label>
          <textarea rows={4} value={form.previous_companies_text} onChange={(e) => updateField("previous_companies_text", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label>{t("summary")}</label>
          <textarea rows={6} value={form.summary} onChange={(e) => updateField("summary", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label>{t("add_note_update")}</label>
          <textarea rows={3} value={form.note} onChange={(e) => updateField("note", e.target.value)}  readOnly={isViewOnly} disabled={isViewOnly} />
        </div>
        {!isViewOnly ? <div style={{ marginTop: 16 }}>
          <button onClick={onSave} disabled={!canSave || !isOwner}>
            {saving ? t("saving") : t("save_changes")}
          </button>
        </div> : null}
        {message && <p style={{ color: "green" }}>{message}</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>

{!isViewOnly && (
      <div className="grid grid-2">
        <div className="card">
          <h3>{t("interview_scheduling")}</h3>
          <div className="grid grid-2">
            <div>
              <label>{t("interviewer_email")}</label>
              <input
                value={schedInterviewer}
                onChange={(e) => setSchedInterviewer(e.target.value)}
                placeholder="interviewer@company.com"
              />
            </div>
            <div>
              <label>{t("scheduled_at")}</label>
              <input type="datetime-local" value={schedAt} onChange={(e) => setSchedAt(e.target.value)} />
            </div>
            <div>
              <label>{t("duration_mins")}</label>
              <input type="number" min={15} value={schedDuration} onChange={(e) => setSchedDuration(e.target.value)} />
            </div>
            <div>
              <label>{t("meeting_link")}</label>
              <input value={schedLink} onChange={(e) => setSchedLink(e.target.value)} placeholder="https://meet..." />
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <label>{t("notes")}</label>
            <textarea rows={2} value={schedNotes} onChange={(e) => setSchedNotes(e.target.value)} />
          </div>
          <button style={{ marginTop: 8 }} onClick={onScheduleInterview} disabled={!isOwner}>
            {t("schedule_interview")}
          </button>
          <div className="timeline" style={{ marginTop: 12 }}>
            {schedules.map((s) => (
              <div className="timeline-item" key={s.id}>
                <div className="timeline-dot" />
                <div>
                  <div>
                    <strong>{new Date(s.scheduled_at).toLocaleString()}</strong> {t("with_label")} {s.interviewer_email}
                  </div>
                  <small>{s.duration_minutes} {t("mins_label")}</small>
                </div>
              </div>
            ))}
            {!schedules.length && <small>{t("no_schedules")}</small>}
          </div>
        </div>

        <div className="card">
          <h3>{t("interview_scorecards")}</h3>
          <div className="grid grid-2">
            <div>
              <label>{t("technical")}</label>
              <input type="number" min={1} max={5} value={scoreTech} onChange={(e) => setScoreTech(e.target.value)} />
            </div>
            <div>
              <label>{t("communication")}</label>
              <input type="number" min={1} max={5} value={scoreComm} onChange={(e) => setScoreComm(e.target.value)} />
            </div>
            <div>
              <label>{t("problem_solving")}</label>
              <input type="number" min={1} max={5} value={scoreProblem} onChange={(e) => setScoreProblem(e.target.value)} />
            </div>
            <div>
              <label>{t("overall")}</label>
              <input type="number" min={1} max={5} value={scoreOverall} onChange={(e) => setScoreOverall(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-2" style={{ marginTop: 10 }}>
            <div>
              <label>{t("recommendation")}</label>
              <select value={scoreRecommendation} onChange={(e) => setScoreRecommendation(e.target.value)}>
                <option value="strong_yes">Strong Yes</option>
                <option value="yes">Yes</option>
                <option value="neutral">Neutral</option>
                <option value="no">No</option>
                <option value="strong_no">Strong No</option>
              </select>
            </div>
            <div>
              <label>{t("summary")}</label>
              <textarea rows={3} value={scoreSummary} onChange={(e) => setScoreSummary(e.target.value)} />
            </div>
          </div>
          <button style={{ marginTop: 10 }} onClick={onAddScorecard} disabled={!isOwner}>
            {t("submit_scorecard")}
          </button>

          <div className="timeline" style={{ marginTop: 12 }}>
            {scorecards.map((s) => (
              <div className="timeline-item" key={s.id}>
                <div className="timeline-dot" />
                <div>
                  <div>
                    Stage: <strong>{s.interview_stage}</strong> | Overall: <strong>{s.overall_score ?? "-"}</strong>
                  </div>
                  <small>
                    Tech {s.criteria_scores?.technical ?? "-"}, Comm {s.criteria_scores?.communication ?? "-"}, Problem {" "}
                    {s.criteria_scores?.problem_solving ?? "-"}
                  </small>
                </div>
              </div>
            ))}
            {!scorecards.length && <small>{t("no_scorecards")}</small>}
          </div>
        </div>
      </div>
      )}

      {isViewOnly && (
        <div className="card">
          <h3>{t("interview_scorecards")}</h3>
          <div className="timeline" style={{ marginTop: 12 }}>
            {scorecards.map((s) => (
              <div className="timeline-item" key={s.id}>
                <div className="timeline-dot" />
                <div>
                  <div>
                    Stage: <strong>{s.interview_stage}</strong> | Overall: <strong>{s.overall_score ?? "-"}</strong>
                  </div>
                  <small>
                    Tech {s.criteria_scores?.technical ?? "-"}, Comm {s.criteria_scores?.communication ?? "-"}, Problem {" "}
                    {s.criteria_scores?.problem_solving ?? "-"}
                  </small>
                </div>
              </div>
            ))}
            {!scorecards.length && <small>{t("no_scorecards")}</small>}
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <div className="card">
          <h3>{t("comments_mentions")}</h3>
          <small>{t("mention_hint")}</small>
          <div style={{ marginTop: 10 }}>
            <textarea
              rows={3}
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Example: @john please review this candidate"
            />
            <button style={{ marginTop: 8 }} onClick={onAddComment}>
              {t("add_comment")}
            </button>
          </div>
          <div className="timeline" style={{ marginTop: 12 }}>
            {comments.map((c) => (
              <div className="timeline-item" key={c.id}>
                <div className="timeline-dot" />
                <div>
                  <div><strong>{c.author_name || `User #${c.author_user_id}`}</strong></div>
                  <div style={{ marginTop: 4 }}>{c.body}</div>
                  {!!c.mentions?.length && <small>{t("mentions_label")}: {c.mentions.map((m) => `@${m}`).join(", ")}</small>}
                  <br />
                  <small>{new Date(c.created_at).toLocaleString()}</small>
                </div>
              </div>
            ))}
            {!comments.length && <small>{t("no_comments")}</small>}
          </div>
        </div>

        {!isViewOnly && isOwner ? <div className="card">
          <h3>Ownership Requests Inbox</h3>
          <small>Approve or reject transfer requests from other HR members.</small>
          <div className="timeline" style={{ marginTop: 10 }}>
            {pendingOwnershipRequests.map((r: any) => (
              <div id={`req-${r.id}`} key={r.id} className="timeline-item">
                <div className="timeline-dot" />
                <div>
                  <div><strong>{r.from_email}</strong> requested ownership</div>{r.reason ? <small>Reason: {r.reason}</small> : null}
                  <small>{r.created_at}</small>
                  <div className="toolbar-actions" style={{ marginTop: 6 }}>
                    <button style={{ width: "auto" }} onClick={() => onOwnershipDecision(r.id, "approve")}>Approve</button>
                    <button className="btn-outline" style={{ width: "auto" }} onClick={() => onOwnershipDecision(r.id, "reject")}>Reject</button>
                  </div>
                </div>
              </div>
            ))}
            {!pendingOwnershipRequests.length && <small>No pending requests.</small>}
          </div>
        </div> : null}

        {!isViewOnly && isOwner ? <div className="card">
          <h3>Team Collaboration Sharing</h3>
          <small>Send sharing invitation to another HR. They can approve to create their own cloned candidate record.</small>
          <div className="toolbar-actions" style={{ marginTop: 8 }}>
            <input style={{ maxWidth: 260 }} value={shareEmail} onChange={(e) => setShareEmail(e.target.value)} placeholder="hr@company.com" />
            <input style={{ maxWidth: 320 }} value={shareReason} onChange={(e) => setShareReason(e.target.value)} placeholder="Reason (optional)" />
            <button style={{ width: "auto" }} onClick={onShareCandidate}>Send invite</button>
          </div>
          <div className="chip-wrap" style={{ marginTop: 10 }}>
            {((candidate.parsed_json as any)?.collaborator_emails || []).map((em: string) => (
              <span key={em} className="chip">
                {em}
                <button className="btn-outline" style={{ width: "auto", marginLeft: 8, padding: "2px 6px" }} onClick={() => onUnshareCandidate(em)}>x</button>
              </span>
            ))}
            {!((candidate.parsed_json as any)?.collaborator_emails || []).length && <small>No direct collaborators yet (invite-based clone flow enabled).</small>}
          </div>
        </div> : null}

        {!isViewOnly ? <div className="card">
          <h3>{t("candidate_timeline")}</h3>
          <div className="timeline timeline-scroll">
            {timelineOf(candidate).map((event, idx) => (
              <div className="timeline-item" key={`${event.timestamp}-${idx}`}>
                <div className="timeline-dot" />
                <div>
                  <div className="timeline-title">{formatTimelineTitle(lang, event.type)}</div>
                  <div>{formatTimelineEvent(lang, event)}</div>
                  <small>{formatTimelineTime(lang, event.timestamp)}</small>
                </div>
              </div>
            ))}
            {!timelineOf(candidate).length && <small>{t("no_timeline")}</small>}
          </div>
        </div> : null}
      </div>
    </div>
  );
}
