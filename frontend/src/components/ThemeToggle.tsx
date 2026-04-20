"use client";

import { useEffect, useState } from "react";

type ThemeMode = "light" | "dark";

function applyTheme(mode: ThemeMode) {
  document.documentElement.setAttribute("data-theme", mode);
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>("light");

  useEffect(() => {
    const saved = localStorage.getItem("mini_ats_theme") as ThemeMode | null;
    const initial: ThemeMode = saved === "dark" ? "dark" : "light";
    setTheme(initial);
    applyTheme(initial);
  }, []);

  const onToggle = () => {
    const next: ThemeMode = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("mini_ats_theme", next);
    applyTheme(next);
  };

  return (
    <button type="button" className="btn-outline" onClick={onToggle} style={{ width: "auto" }}>
      {theme === "light" ? "🌙 Dark" : "☀️ Light"}
    </button>
  );
}
