"use client";

export type CandidateTab = "profile" | "interviews" | "notes" | "timeline";

export default function CandidateTabs({ activeTab, onTab }: { activeTab: CandidateTab; onTab: (t: CandidateTab) => void }) {
  return (
    <div className="card section-nav-card">
      <div className="toolbar" style={{ alignItems: "center" }}>
        <div><h3 style={{ margin: 0 }}>Candidate Workspace</h3><small>Use tabs to focus your workflow.</small></div>
        <div className="toolbar-actions">
          <button className={activeTab === "profile" ? "" : "btn-outline"} style={{ width: "auto" }} onClick={() => onTab("profile")}>Profile</button>
          <button className={activeTab === "interviews" ? "" : "btn-outline"} style={{ width: "auto" }} onClick={() => onTab("interviews")}>Interviews</button>
          <button className={activeTab === "notes" ? "" : "btn-outline"} style={{ width: "auto" }} onClick={() => onTab("notes")}>Notes</button>
          <button className={activeTab === "timeline" ? "" : "btn-outline"} style={{ width: "auto" }} onClick={() => onTab("timeline")}>Timeline</button>
        </div>
      </div>
    </div>
  );
}
