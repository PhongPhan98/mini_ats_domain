"use client";

import { useEffect, useState } from "react";
import { useAppLanguage } from "../lib/language";

export default function CompactModeToggle() {
  const [compact, setCompact] = useState(false);
  const { t } = useAppLanguage();

  useEffect(() => {
    const saved = localStorage.getItem("mini_ats_compact_mode") === "1";
    setCompact(saved);
    document.documentElement.setAttribute("data-compact", saved ? "1" : "0");
  }, []);

  const toggle = () => {
    const next = !compact;
    setCompact(next);
    localStorage.setItem("mini_ats_compact_mode", next ? "1" : "0");
    document.documentElement.setAttribute("data-compact", next ? "1" : "0");
  };

  return (
    <button
      type="button"
      className="btn-outline"
      style={{ width: "auto" }}
      onClick={toggle}
    >
      {compact ? `📏 ${t("spacious")}` : `🗜️ ${t("compact")}`}
    </button>
  );
}
