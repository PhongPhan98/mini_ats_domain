"use client";
import { useAppLanguage } from "../lib/language";

export type CandidateTab = "profile" | "interviews" | "notes" | "timeline";

export default function CandidateTabs({
  activeTab,
  onTab,
}: {
  activeTab: CandidateTab;
  onTab: (t: CandidateTab) => void;
}) {
  const { t } = useAppLanguage();
  return (
    <div className="card section-nav-card">
      <div className="toolbar" style={{ alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>{t("candidate_workspace")}</h3>
          <small>{t("workspace_hint")}</small>
        </div>
        <div className="toolbar-actions">
          <button
            className={activeTab === "profile" ? "" : "btn-outline"}
            style={{ width: "auto" }}
            onClick={() => onTab("profile")}
          >
            {t("profile")}
          </button>
          <button
            className={activeTab === "interviews" ? "" : "btn-outline"}
            style={{ width: "auto" }}
            onClick={() => onTab("interviews")}
          >
            {t("interviews")}
          </button>
          <button
            className={activeTab === "notes" ? "" : "btn-outline"}
            style={{ width: "auto" }}
            onClick={() => onTab("notes")}
          >
            {t("notes")}
          </button>
          <button
            className={activeTab === "timeline" ? "" : "btn-outline"}
            style={{ width: "auto" }}
            onClick={() => onTab("timeline")}
          >
            {t("timeline")}
          </button>
        </div>
      </div>
    </div>
  );
}
