"use client";

import { apiUrl } from "../../lib/api";

export default function LoginPage() {
  const login = () => {
    window.location.href = apiUrl("/api/auth/google/login");
  };

  return (
    <div className="login-wrap page-enter">
      <div className="card login-card">
        <div className="login-badge">Mini ATS</div>
        <h1>Welcome back 👋</h1>
        <p className="muted">Sign in with your Google account to continue to candidate pipeline, jobs and collaboration.</p>

        <button className="login-google-btn" onClick={login}>
          <span>🔐</span>
          <span>Continue with Google</span>
        </button>

        <div className="login-hints">
          <div className="chip">Secure cookie session</div>
          <div className="chip">Role-based access</div>
          <div className="chip">Personal data isolation</div>
        </div>
      </div>
    </div>
  );
}
