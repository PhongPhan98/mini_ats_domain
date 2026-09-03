"use client";

import { useEffect, useState } from "react";

export type AppLang = "en" | "vi";

const STORAGE_KEY = "miniats_lang";
const EVENT_NAME = "miniats:lang-change";

export const text = {
  en: {
    nav_dashboard: "Dashboard",
    nav_pipeline: "Pipeline",
    nav_automation: "Automation",
    nav_upload: "Upload CV",
    nav_jobs: "Jobs & Matching",
    nav_candidates: "Candidates",
    nav_notifications: "Notifications",
    nav_activity: "Activity",
    nav_users: "Users",
    nav_audit: "Audit",
    nav_permissions: "Permissions",

    dashboard_title: "Recruitment Dashboard",
    report_candidates_csv: "Candidates CSV",
    report_analytics_csv: "Analytics CSV",
    report_xlsx: "XLSX",
    report_pdf: "PDF",

    upload_title: "Upload CV",
    upload_supported: "Supported formats: PDF, DOCX",
    upload_action: "Upload & Parse with AI",
    uploading: "Uploading...",
    upload_failed: "Upload failed",
    parsed_candidate: "Parsed Candidate",
    raw_json: "Raw JSON",

    pipeline_title: "Recruitment Pipeline",
    pipeline_hint:
      "Drag candidates between stages to update status and trigger automation.",
    search_placeholder: "Search by name/email/skills",
    no_candidates: "No candidates",
    open: "Open",

    jobs_title: "Jobs & Matching",
    jobs_hint: "Create jobs, then run AI matching against candidate pool.",
    create_job: "Create Job",
    job_title: "Job title",
    enter_requirements: "Enter requirements",
    save_job: "Save Job",
    job_list: "Job List",
    created: "Created",
    actions: "Actions",
    running: "Running...",
    run_matching: "Run Matching",
    no_jobs: "No jobs yet.",
    match_results: "Match Results",
    candidate: "Candidate",
    score: "Score",
    explanation: "Explanation",

    automation_title: "Automation Rules",
    automation_hint: "Trigger log/email/webhook actions on stage changes.",
    rules: "Rules",
    add_rule: "Add Rule",
    save_rules: "Save Rules",
    saving: "Saving...",
    no_rules: "No automation rules yet.",
    event_log: "Automation Event Log",
    time: "Time",
    stage: "Stage",
    rule: "Rule",
    result: "Result",
    no_events: "No events yet.",
    back_to_active: "Back to Active",
    trash: "Trash",

    schedule_success: "Interview scheduled successfully",
    update_success: "Information saved successfully",
    save_failed: "Save failed",
    parse_warning:
      "Could not extract full CV content. Please try another file or cleaner PDF.",

    candidate_detail: "Candidate Detail",
    back: "Back",
    no_email: "No email",
    profile_information: "Profile Information",
    name: "Name",
    email: "Email",
    phone: "Phone",
    years_experience: "Years of experience",
    skills_csv: "Skills (comma-separated)",
    education: "Education",
    previous_companies: "Previous companies",
    summary: "Summary",
    domain_tags: "Domain tags",
    notice_period: "Notice period",
    preferred_location: "Preferred location",
    experience_details: "Experience details",
    achievements: "Achievements",
    add_note_update: "Add note update",
    save_changes: "Save changes",
    stage_quick_actions: "Stage control and quick actions",
    original_cv_files: "Original CV Files",
    view_only_access:
      "View-only access: you can comment and request ownership; only owner can edit candidate profile.",
    request_ownership: "Request ownership",
    reason_request_ownership: "Reason to request ownership",
    move_stage: "Move Stage",
    send_interview_email: "Send Interview Email",
    send_rejection_email: "Send Rejection Email",
    reject: "Reject",
    ownership_request_sent: "Ownership request sent",
    login_google: "Login Google",
    logout: "Logout",
    compact: "Compact",
    spacious: "Spacious",
    dark: "Dark",
    light: "Light",
    candidate_workspace: "Candidate Workspace",
    workspace_hint: "Use tabs to focus your workflow.",
    profile: "Profile",
    interviews: "Interviews",
    timeline: "Timeline",
    interview_scheduling: "Interview Scheduling",
    interviewer_email: "Interviewer Email",
    scheduled_at: "Scheduled At",
    duration_mins: "Duration (mins)",
    meeting_link: "Meeting Link",
    notes: "Notes",
    schedule_interview: "Schedule Interview",
    no_schedules: "No schedules yet.",
    interview_scorecards: "Interview Scorecards",
    technical: "Technical (1-5)",
    communication: "Communication (1-5)",
    problem_solving: "Problem Solving (1-5)",
    overall: "Overall",
    recommendation: "Recommendation",
    submit_scorecard: "Submit Scorecard",
    no_scorecards: "No scorecards yet.",
    comments_mentions: "Comments & Mentions",
    mention_hint: "Use @username or @emailprefix to mention teammates.",
    add_comment: "Add Comment",
    no_comments: "No comments yet.",
    candidate_timeline: "Candidate Timeline",
    no_timeline: "No timeline events yet.",
    missing_required_fields: "Please fill required fields first",

    loading_candidate: "Loading candidate...",
    candidate_not_found: "Candidate not found.",
    stage_label: "Stage",
    with_label: "with",
    mins_label: "mins",
    mentions_label: "Mentions",
    no_files_selected: "No files selected",
    files_selected: "files selected",
    imported_cvs: "Imported CVs",
    avg_readiness: "Avg readiness",
  },
  vi: {
    nav_dashboard: "Tổng quan",
    nav_pipeline: "Pipeline",
    nav_automation: "Tự động",
    nav_upload: "Nhập CV",
    nav_jobs: "Việc làm",
    nav_candidates: "Ứng viên",
    nav_notifications: "Thông báo",
    nav_activity: "Hoạt động",
    nav_users: "Người dùng",
    nav_audit: "Kiểm toán",
    nav_permissions: "Phân quyền",

    dashboard_title: "Bảng điều khiển tuyển dụng",
    report_candidates_csv: "CSV ứng viên",
    report_analytics_csv: "CSV phân tích",
    report_xlsx: "Tệp XLSX",
    report_pdf: "Tệp PDF",

    upload_title: "Tải CV",
    upload_supported: "Định dạng hỗ trợ: PDF, DOCX",
    upload_action: "Tải lên & Phân tích bằng AI",
    uploading: "Đang tải lên...",
    upload_failed: "Tải lên thất bại",
    parsed_candidate: "Ứng viên đã phân tích",
    raw_json: "JSON thô",

    pipeline_title: "Quy trình tuyển dụng",
    pipeline_hint:
      "Kéo thả ứng viên giữa các giai đoạn để cập nhật trạng thái và kích hoạt tự động hoá.",
    search_placeholder: "Tìm theo tên/email/kỹ năng",
    no_candidates: "Chưa có ứng viên",
    open: "Mở",

    jobs_title: "Việc làm & Ghép ứng viên",
    jobs_hint: "Tạo việc làm, sau đó chạy AI để ghép với danh sách ứng viên.",
    create_job: "Tạo việc làm",
    job_title: "Tiêu đề việc làm",
    enter_requirements: "Nhập yêu cầu",
    save_job: "Lưu việc làm",
    job_list: "Danh sách việc làm",
    created: "Ngày tạo",
    actions: "Thao tác",
    running: "Đang chạy...",
    run_matching: "Chạy ghép ứng viên",
    no_jobs: "Chưa có việc làm.",
    match_results: "Kết quả ghép",
    candidate: "Ứng viên",
    score: "Điểm",
    explanation: "Giải thích",

    automation_title: "Quy tắc tự động hoá",
    automation_hint: "Kích hoạt log/email/webhook khi thay đổi giai đoạn.",
    rules: "Quy tắc",
    add_rule: "Thêm quy tắc",
    save_rules: "Lưu quy tắc",
    saving: "Đang lưu...",
    no_rules: "Chưa có quy tắc tự động hoá.",
    event_log: "Nhật ký tự động hoá",
    time: "Thời gian",
    stage: "Giai đoạn",
    rule: "Quy tắc",
    result: "Kết quả",
    no_events: "Chưa có sự kiện.",
    back_to_active: "Quay lại danh sách",
    trash: "Thùng rác",

    schedule_success: "Đã lên lịch phỏng vấn thành công",
    update_success: "Đã lưu thông tin thành công",
    save_failed: "Lưu thất bại",
    parse_warning:
      "Không thể trích xuất đầy đủ nội dung CV. Hãy thử file khác hoặc PDF rõ hơn.",

    candidate_detail: "Chi tiết ứng viên",
    back: "Quay lại",
    no_email: "Không có email",
    profile_information: "Thông tin hồ sơ",
    name: "Tên",
    email: "Email",
    phone: "Số điện thoại",
    years_experience: "Số năm kinh nghiệm",
    skills_csv: "Kỹ năng (phân tách dấu phẩy)",
    education: "Học vấn",
    previous_companies: "Công ty trước đây",
    summary: "Tóm tắt",
    domain_tags: "Nhãn lĩnh vực",
    notice_period: "Thời gian báo trước",
    preferred_location: "Địa điểm mong muốn",
    experience_details: "Chi tiết kinh nghiệm",
    achievements: "Thành tích",
    add_note_update: "Thêm ghi chú cập nhật",
    save_changes: "Lưu thay đổi",
    stage_quick_actions: "Điều khiển vòng và thao tác nhanh",
    original_cv_files: "Tệp CV gốc",
    view_only_access:
      "Quyền chỉ xem: bạn có thể bình luận và yêu cầu chuyển quyền; chỉ chủ sở hữu được sửa hồ sơ.",
    request_ownership: "Yêu cầu quyền sở hữu",
    reason_request_ownership: "Lý do yêu cầu quyền sở hữu",
    move_stage: "Chuyển vòng",
    send_interview_email: "Gửi email phỏng vấn",
    send_rejection_email: "Gửi email từ chối",
    reject: "Từ chối",
    ownership_request_sent: "Đã gửi yêu cầu quyền sở hữu",
    login_google: "Đăng nhập Google",
    logout: "Đăng xuất",
    compact: "Thu gọn",
    spacious: "Mở rộng",
    dark: "Tối",
    light: "Sáng",
    candidate_workspace: "Không gian ứng viên",
    workspace_hint: "Dùng các thẻ để tập trung vào quy trình.",
    profile: "Hồ sơ",
    interviews: "Phỏng vấn",
    timeline: "Dòng thời gian",
    interview_scheduling: "Lên lịch phỏng vấn",
    interviewer_email: "Email người phỏng vấn",
    scheduled_at: "Thời gian phỏng vấn",
    duration_mins: "Thời lượng (phút)",
    meeting_link: "Link họp",
    notes: "Ghi chú",
    schedule_interview: "Lên lịch phỏng vấn",
    no_schedules: "Chưa có lịch phỏng vấn.",
    interview_scorecards: "Phiếu đánh giá phỏng vấn",
    technical: "Kỹ thuật (1-5)",
    communication: "Giao tiếp (1-5)",
    problem_solving: "Giải quyết vấn đề (1-5)",
    overall: "Tổng quan",
    recommendation: "Đề xuất",
    submit_scorecard: "Gửi phiếu đánh giá",
    no_scorecards: "Chưa có phiếu đánh giá.",
    comments_mentions: "Bình luận & Gắn nhắc",
    mention_hint: "Dùng @username hoặc @emailprefix để nhắc đồng đội.",
    add_comment: "Thêm bình luận",
    no_comments: "Chưa có bình luận.",
    candidate_timeline: "Dòng thời gian ứng viên",
    no_timeline: "Chưa có sự kiện dòng thời gian.",
    missing_required_fields: "Vui lòng nhập đủ thông tin bắt buộc",

    loading_candidate: "Đang tải ứng viên...",
    candidate_not_found: "Không tìm thấy ứng viên.",
    stage_label: "Vòng",
    with_label: "với",
    mins_label: "phút",
    mentions_label: "Gắn nhắc",
    no_files_selected: "Chưa chọn tệp",
    files_selected: "tệp đã chọn",
    imported_cvs: "CV đã nhập",
    avg_readiness: "Độ sẵn sàng TB",
  },
} as const;

function getStoredLang(): AppLang {
  if (typeof window === "undefined") return "en";
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === "vi" ? "vi" : "en";
}

export function useAppLanguage() {
  const [lang, setLangState] = useState<AppLang>("en");

  useEffect(() => {
    const initial = getStoredLang();
    setLangState(initial);
    document.documentElement.lang = initial;

    const onLangChange = (e: Event) => {
      const detail = (e as CustomEvent<{ lang: AppLang }>).detail;
      if (detail?.lang) {
        setLangState(detail.lang);
        document.documentElement.lang = detail.lang;
      }
    };

    window.addEventListener(EVENT_NAME, onLangChange);
    return () => window.removeEventListener(EVENT_NAME, onLangChange);
  }, []);

  const setLang = (next: AppLang) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, next);
    window.dispatchEvent(
      new CustomEvent(EVENT_NAME, { detail: { lang: next } }),
    );
  };

  const t = (key: keyof typeof text.en) => text[lang][key] || text.en[key];

  return { lang, setLang, t };
}
