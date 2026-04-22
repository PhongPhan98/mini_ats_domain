"use client";

import { useAppLanguage } from "../lib/language";

export default function LanguageToggle() {
  const { lang, setLang } = useAppLanguage();

  return (
    <button
      type="button"
      className="btn-outline nav-toggle"
      onClick={() => setLang(lang === "en" ? "vi" : "en")}
      title="Toggle language"
    >
      {lang === "en" ? "EN → VI" : "VI → EN"}
    </button>
  );
}
