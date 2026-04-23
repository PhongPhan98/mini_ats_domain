"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import CompactModeToggle from "./CompactModeToggle";
import ThemeToggle from "./ThemeToggle";
import LanguageToggle from "./LanguageToggle";
import AuthStatus from "./AuthStatus";
import { useAppLanguage } from "../lib/language";
import { useMe } from "../lib/me";

export default function NavBar() {
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const { t } = useAppLanguage();
  const { me } = useMe();

  const isActive = (href: string) => pathname === href;

  return (
    <nav className="card nav-bar">
      {!isLogin && <div className="nav-links">
        <Link className={isActive("/") ? "nav-link nav-link-active" : "nav-link"} href="/">{t("nav_dashboard")}</Link>
        <Link className={isActive("/pipeline") ? "nav-link nav-link-active" : "nav-link"} href="/pipeline">{t("nav_pipeline")}</Link>
        <Link className={isActive("/automation") ? "nav-link nav-link-active" : "nav-link"} href="/automation">{t("nav_automation")}</Link>
        <Link className={isActive("/upload") ? "nav-link nav-link-active" : "nav-link"} href="/upload">{t("nav_upload")}</Link>
        <Link className={isActive("/jobs") ? "nav-link nav-link-active" : "nav-link"} href="/jobs">{t("nav_jobs")}</Link>
        {me?.role === "admin" && <Link className={isActive("/users") ? "nav-link nav-link-active" : "nav-link"} href="/users">Users</Link>}
        {me?.role === "admin" && <Link className={isActive("/audit") ? "nav-link nav-link-active" : "nav-link"} href="/audit">Audit</Link>}
      </div>}
      <div className="nav-actions">
        <LanguageToggle />
        <CompactModeToggle />
        <ThemeToggle />
        <AuthStatus />
      </div>
    </nav>
  );
}
