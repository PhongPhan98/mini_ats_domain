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
    pipeline_hint: "Drag candidates between stages to update status and trigger automation.",
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

    schedule_success: "Interview scheduled successfully",
    update_success: "Information saved successfully",
    save_failed: "Save failed",
    parse_warning: "Could not extract full CV content. Please try another file or cleaner PDF.",
  },
  vi: {
    nav_dashboard: "Bảng điều khiển",
    nav_pipeline: "Quy trình",
    nav_automation: "Tự động hoá",
    nav_upload: "Tải CV",
    nav_jobs: "Việc làm & Ghép ứng viên",

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
    pipeline_hint: "Kéo thả ứng viên giữa các giai đoạn để cập nhật trạng thái và kích hoạt tự động hoá.",
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

    schedule_success: "Đã lên lịch phỏng vấn thành công",
    update_success: "Đã lưu thông tin thành công",
    save_failed: "Lưu thất bại",
    parse_warning: "Không thể trích xuất đầy đủ nội dung CV. Hãy thử file khác hoặc PDF rõ hơn.",
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
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { lang: next } }));
  };

  const t = (key: keyof typeof text.en) => text[lang][key] || text.en[key];

  return { lang, setLang, t };
}
