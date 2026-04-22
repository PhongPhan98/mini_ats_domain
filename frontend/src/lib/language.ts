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
