"use client";

import { useEffect, useState } from "react";
import { apiGet } from "./api";

export function useMe() {
  const [me, setMe] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await apiGet<any>("/api/auth/me");
        if (active) setMe(data);
      } catch {
        if (active) setMe(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  return { me, loading };
}
