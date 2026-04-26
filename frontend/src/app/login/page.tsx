"use client";

import { useState } from "react";
import { apiUrl } from "../../lib/api";

export default function LoginPage() {
  const [redirecting, setRedirecting] = useState(false);

  const login = () => {
    setRedirecting(true);
    window.location.href = apiUrl("/api/auth/google/login");
  };

  return (
    <div className="login-wrap page-enter">
      <div className="card login-card">
        <div className="login-logo">🧑‍💼</div>
        <div className="login-badge">Mini ATS</div>
        <h1>Welcome back 👋</h1>
        <p className="muted">Sign in with your Google account to continue to candidate pipeline, jobs and collaboration.</p>
        <small className="login-subline">Use your approved work account for best access experience.</small>

        <button className="login-google-btn" onClick={login} disabled={redirecting}>
          <span>{redirecting ? "⏳" : "🔐"}</span>
          <span>{redirecting ? "Redirecting to Google..." : "Continue with Google"}</span>
        </button>

        <div className="login-hints">
          <div className="chip">Secure cookie session</div>
          <div className="chip">Role-based access</div>
          <div className="chip">Personal data isolation</div>
        </div>

        <div className="login-help">Need help signing in? Check Google account access or contact admin.</div>
      </div>
    </div>
  );
}
