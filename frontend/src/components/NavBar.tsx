"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import CompactModeToggle from "./CompactModeToggle";
import ThemeToggle from "./ThemeToggle";
import LanguageToggle from "./LanguageToggle";
import AuthStatus from "./AuthStatus";
import { useAppLanguage } from "../lib/language";
import { useMe } from "../lib/me";
import { apiGet } from "../lib/api";

export default function NavBar() {
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isPublicJob = pathname.startsWith("/jobs/") || pathname === "/privacy" || pathname === "/careers";
  const { t } = useAppLanguage();
  const { me } = useMe();
  const [mentionCount, setMentionCount] = useState(0);

  useEffect(() => {
    if (!me) return;
    (async () => {
      try {
        const [m, rq, inv] = await Promise.all([
          apiGet<{ mentions: any[] }>("/api/candidates/notifications/mentions"),
          apiGet<{ requests: any[] }>(
            "/api/candidates/ownership/requests?scope=inbox",
          ),
          apiGet<{ invitations: any[] }>(
            "/api/candidates/share/invitations?scope=inbox",
          ),
        ]);
        const all = [
          ...(m.mentions || []),
          ...(rq.requests || []),
          ...(inv.invitations || []),
        ].map((x: any) => x.created_at || x.updated_at || "");
        const seen = localStorage.getItem("miniats_notif_seen_at") || "";
        const unread = all.filter((ts: string) => ts && ts > seen).length;
        setMentionCount(unread);
      } catch {
        setMentionCount(0);
      }
    })();
  }, [me?.id]);

  const isActive = (href: string) =>
    pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));

  const mainLinks = [
    { href: "/dashboard", label: t("nav_dashboard") },
    { href: "/pipeline", label: t("nav_pipeline") },
    { href: "/candidates", label: t("nav_candidates") },
    { href: "/jobs", label: t("nav_jobs") },
  ];

  const toolLinks = [
    { href: "/offers", label: "Offers" },
    { href: "/automation", label: t("nav_automation") },
    { href: "/activity", label: t("nav_activity") },
  ];

  if (isPublicJob) {
    return (
      <nav className="nav-bar public-nav" aria-label="Career site navigation">
        <Link href="/careers" className="nav-brand"><span className="nav-brand-mark">M</span><span><strong>Careers</strong><small>Join our team</small></span></Link>
        <div className="nav-actions"><Link className="nav-link" href="/privacy">Privacy</Link><ThemeToggle /></div>
      </nav>
    );
  }

  if (isLogin) {
    return (
      <nav className="nav-bar nav-login" aria-label="Sign-in navigation">
        <Link className="nav-brand" href="/login" aria-label="Mini ATS sign in">
          <span className="nav-brand-mark">M</span>
          <span><strong>Mini ATS</strong><small>Recruiting workspace</small></span>
        </Link>
        <div className="nav-actions">
          <Link className="nav-link" href="/careers">Careers</Link>
          <Link className="nav-link" href="/privacy">Privacy</Link>
          <ThemeToggle />
        </div>
      </nav>
    );
  }

  return (
    <nav className="nav-bar" aria-label="Main navigation">
          <Link className="nav-brand" href="/dashboard" aria-label="Mini ATS dashboard">
            <span className="nav-brand-mark">M</span>
            <span><strong>Mini ATS</strong><small>Recruiting workspace</small></span>
          </Link>
          <div className="nav-links">
          {mainLinks.map((item) => (
            <Link key={item.href} className={isActive(item.href) ? "nav-link nav-link-active" : "nav-link"} href={item.href}>
              {item.label}
            </Link>
          ))}
          <Link className="nav-link nav-link-primary" href="/upload">
            <span aria-hidden="true">+</span> {t("nav_upload")}
          </Link>
          <details className="nav-more">
            <summary className="nav-link">More</summary>
            <div className="nav-more-menu">
              {toolLinks.map((item) => (
                <Link key={item.href} className={isActive(item.href) ? "nav-link nav-link-active" : "nav-link"} href={item.href}>{item.label}</Link>
              ))}
          <Link
            className={
              isActive("/notifications")
                ? "nav-link nav-link-active"
                : "nav-link"
            }
            href="/notifications"
          >
            {t("nav_notifications")}
            {mentionCount > 0 ? (
              <span className="chip" style={{ marginLeft: 6 }}>
                {mentionCount}
              </span>
            ) : null}
          </Link>
          {me?.role === "admin" && (
            <Link
              className={
                isActive("/users") ? "nav-link nav-link-active" : "nav-link"
              }
              href="/users"
            >
              {t("nav_users")}
            </Link>
          )}
          {me?.role === "admin" && (
            <Link
              className={
                isActive("/audit") ? "nav-link nav-link-active" : "nav-link"
              }
              href="/audit"
            >
              {t("nav_audit")}
            </Link>
          )}
          {me?.role === "admin" && (
            <Link
              className={
                isActive("/permissions")
                  ? "nav-link nav-link-active"
                  : "nav-link"
              }
              href="/permissions"
            >
              {t("nav_permissions")}
            </Link>
          )}
            </div>
          </details>
        </div>
      <div className="nav-actions">
        <LanguageToggle />
        <CompactModeToggle />
        <ThemeToggle />
        <AuthStatus />
      </div>
    </nav>
  );
}
