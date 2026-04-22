"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import CompactModeToggle from "./CompactModeToggle";
import ThemeToggle from "./ThemeToggle";
import LanguageToggle from "./LanguageToggle";
import { useAppLanguage } from "../lib/language";

export default function NavBar() {
  const pathname = usePathname();
  const { t } = useAppLanguage();

  const isActive = (href: string) => pathname === href;

  return (
    <nav className="card nav-bar">
      <div className="nav-links">
        <Link className={isActive("/") ? "nav-link nav-link-active" : "nav-link"} href="/">{t("nav_dashboard")}</Link>
        <Link className={isActive("/pipeline") ? "nav-link nav-link-active" : "nav-link"} href="/pipeline">{t("nav_pipeline")}</Link>
        <Link className={isActive("/automation") ? "nav-link nav-link-active" : "nav-link"} href="/automation">{t("nav_automation")}</Link>
        <Link className={isActive("/upload") ? "nav-link nav-link-active" : "nav-link"} href="/upload">{t("nav_upload")}</Link>
        <Link className={isActive("/jobs") ? "nav-link nav-link-active" : "nav-link"} href="/jobs">{t("nav_jobs")}</Link>
      </div>
      <div className="nav-actions">
        <LanguageToggle />
        <CompactModeToggle />
        <ThemeToggle />
      </div>
    </nav>
  );
}
