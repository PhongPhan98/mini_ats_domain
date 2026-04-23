"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

export default function AuthStatus() {
  const [me, setMe] = useState<any>(null);

  const load = async () => {
    try {
      const data = await apiGet<any>("/api/auth/me");
      setMe(data);
    } catch {
      setMe(null);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const login = () => {
    window.location.href = "http://localhost:8000/api/auth/google/login";
  };

  const logout = async () => {
    await apiPost("/api/auth/logout", {});
    setMe(null);
    window.location.reload();
  };

  if (!me) return <button className="btn-outline nav-toggle" onClick={login}>Login Google</button>;

  return (
    <div className="toolbar-actions">
      <span className="chip">{(me.full_name || me.email.split("@")[0])} ({me.role})</span>
      <button className="btn-outline nav-toggle" onClick={logout}>Logout</button>
    </div>
  );
}
