"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiGet } from "../lib/api";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      if (pathname === "/login") {
        if (active) setReady(true);
        return;
      }
      try {
        await apiGet("/api/auth/me");
        if (active) setReady(true);
      } catch {
        router.replace("/login");
      }
    })();
    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (!ready) return <div className="card">Checking authentication...</div>;
  return <>{children}</>;
}
