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

function NavLabel({ full, short }: { full: string; short: string }) {
  return (
    <>
      <span className="label-full">{full}</span>
      <span className="label-short">{short}</span>
    </>
  );
}

export default function NavBar() {
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const { t } = useAppLanguage();
  const { me } = useMe();
  const [mentionCount, setMentionCount] = useState(0);

  useEffect(() => {
    if (!me) return;
    (async () => {
      try {
        const [m, rq, inv] = await Promise.all([
          apiGet<{ mentions: any[] }>("/api/candidates/notifications/mentions"),
          apiGet<{ requests: any[] }>("/api/candidates/ownership/requests?scope=inbox"),
          apiGet<{ invitations: any[] }>("/api/candidates/share/invitations?scope=inbox"),
        ]);
        const all = [...(m.mentions || []), ...(rq.requests || []), ...(inv.invitations || [])].map((x: any) => x.created_at || x.updated_at || "");
        const seen = localStorage.getItem("miniats_notif_seen_at") || "";
        const unread = all.filter((ts: string) => ts && ts > seen).length;
        setMentionCount(unread);
      } catch {
        setMentionCount(0);
      }
    })();
  }, [me?.id]);

  const isActive = (href: string) => pathname === href;

  return (
    <nav className="card nav-bar">
      {!isLogin && <div className="nav-links">
        <Link className={isActive("/") ? "nav-link nav-link-active" : "nav-link"} href="/"><NavLabel full={t("nav_dashboard")} short="Home" /></Link>
        <Link className={isActive("/pipeline") ? "nav-link nav-link-active" : "nav-link"} href="/pipeline"><NavLabel full={t("nav_pipeline")} short="Pipe" /></Link>
        <Link className={isActive("/automation") ? "nav-link nav-link-active" : "nav-link"} href="/automation"><NavLabel full={t("nav_automation")} short="Auto" /></Link>
        <Link className={isActive("/upload") ? "nav-link nav-link-active" : "nav-link"} href="/upload"><NavLabel full={t("nav_upload")} short="Upload" /></Link>
        <Link className={isActive("/jobs") ? "nav-link nav-link-active" : "nav-link"} href="/jobs"><NavLabel full={t("nav_jobs")} short="Jobs" /></Link>
        <Link className={isActive("/notifications") ? "nav-link nav-link-active" : "nav-link"} href="/notifications"><NavLabel full="Notifications" short="Notif" />{mentionCount > 0 ? <span className="chip" style={{ marginLeft: 6 }}>{mentionCount}</span> : null}</Link>
        {me?.role === "admin" && <Link className={isActive("/users") ? "nav-link nav-link-active" : "nav-link"} href="/users"><NavLabel full="Users" short="User" /></Link>}
        {me?.role === "admin" && <Link className={isActive("/audit") ? "nav-link nav-link-active" : "nav-link"} href="/audit"><NavLabel full="Audit" short="Log" /></Link>}
        {me?.role === "admin" && <Link className={isActive("/permissions") ? "nav-link nav-link-active" : "nav-link"} href="/permissions"><NavLabel full="Permissions" short="Perm" /></Link>}
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
