"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiIsAuthenticated, apiUrl } from "../../lib/api";

type AuthConfig = {
  google_enabled: boolean;
  allowed_domain: string | null;
};

function GoogleMark() {
  return (
    <svg aria-hidden="true" className="google-mark" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.55h3.24c1.9-1.75 2.98-4.32 2.98-7.42Z" />
      <path fill="#34A853" d="M12 22c2.7 0 4.98-.9 6.63-2.35l-3.24-2.55c-.9.6-2.05.96-3.39.96-2.61 0-4.83-1.77-5.62-4.14H3.03v2.63A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.38 13.92A6 6 0 0 1 6.07 12c0-.67.11-1.32.31-1.92V7.45H3.03A10 10 0 0 0 2 12c0 1.61.39 3.14 1.03 4.55l3.35-2.63Z" />
      <path fill="#EA4335" d="M12 5.94c1.47 0 2.79.5 3.83 1.5l2.87-2.88A9.63 9.63 0 0 0 12 2a10 10 0 0 0-8.97 5.45l3.35 2.63C7.17 7.71 9.39 5.94 12 5.94Z" />
    </svg>
  );
}

export default function LoginPage() {
  const [checking, setChecking] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const prepareLogin = async () => {
      try {
        if (await apiIsAuthenticated()) {
          window.location.replace("/dashboard");
          return;
        }

        const authConfig = await apiGet<AuthConfig>("/api/auth/config");
        if (active) {
          setConfig(authConfig);
          if (!authConfig.google_enabled) {
            setError("Google sign-in has not been configured for this workspace.");
          }
        }
      } catch {
        if (active) {
          setError("We could not reach the sign-in service. Please try again.");
        }
      } finally {
        if (active) setChecking(false);
      }
    };

    prepareLogin();
    return () => {
      active = false;
    };
  }, []);

  const login = () => {
    if (config && !config.google_enabled) {
      setError("Google sign-in has not been configured for this workspace.");
      return;
    }
    setError("");
    setRedirecting(true);
    window.location.assign(apiUrl("/api/auth/google/login"));
  };

  const busy = checking || redirecting;

  return (
    <main className="login-experience page-enter">
      <section className="login-story" aria-label="Mini ATS overview">
        <div className="login-story-copy">
          <span className="login-kicker"><i /> Recruiting workspace</span>
          <h1>Make every hiring decision easier.</h1>
          <p>
            Keep candidates, interviews, feedback, and offers moving in one
            focused workspace built for hiring teams.
          </p>
          <div className="login-benefits">
            <span><b>01</b> One clear hiring pipeline</span>
            <span><b>02</b> Faster CV review and shortlisting</span>
            <span><b>03</b> Shared decisions with full context</span>
          </div>
        </div>

        <div className="login-product-preview" aria-hidden="true">
          <div className="login-preview-topbar">
            <span className="login-preview-brand"><i>M</i> Mini ATS</span>
            <span className="login-preview-avatar">AP</span>
          </div>
          <div className="login-preview-content">
            <div className="login-preview-heading">
              <div><small>Hiring pipeline</small><strong>Product Designer</strong></div>
              <span>+ Add candidate</span>
            </div>
            <div className="login-preview-metrics">
              <div><small>Active</small><strong>28</strong></div>
              <div><small>Interviews</small><strong>7</strong></div>
              <div><small>Offers</small><strong>3</strong></div>
            </div>
            <div className="login-preview-pipeline">
              <div className="login-preview-column">
                <label>New <span>8</span></label>
                <article><i>LM</i><div><strong>Linh Mai</strong><small>Senior designer</small></div></article>
                <article><i>TN</i><div><strong>Thanh Nguyen</strong><small>Product designer</small></div></article>
              </div>
              <div className="login-preview-column">
                <label>Interview <span>4</span></label>
                <article><i>AK</i><div><strong>Anh Khoa</strong><small>Tomorrow · 10:00</small></div></article>
              </div>
              <div className="login-preview-column">
                <label>Offer <span>2</span></label>
                <article><i>HT</i><div><strong>Ha Tran</strong><small>Offer sent</small></div></article>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="login-entry" aria-labelledby="login-title">
        <div className="login-panel">
          <span className="eyebrow">Welcome back</span>
          <h2 id="login-title">Sign in to your workspace</h2>
          <p className="login-intro">
            Continue with your approved company Google account.
          </p>

          {config?.allowed_domain && (
            <div className="login-domain">For @{config.allowed_domain} accounts</div>
          )}

          <button
            className="login-google-btn"
            type="button"
            onClick={login}
            disabled={busy || config?.google_enabled === false}
            aria-busy={busy}
          >
            {checking ? <span className="login-spinner" /> : <GoogleMark />}
            <span>
              {checking
                ? "Checking your session..."
                : redirecting
                  ? "Opening Google..."
                  : "Continue with Google"}
            </span>
          </button>

          {error && <div className="login-error" role="alert">{error}</div>}

          <div className="login-trust">
            <div className="login-trust-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3 5 6v5c0 4.6 2.9 8.3 7 10 4.1-1.7 7-5.4 7-10V6l-7-3Zm-1 12-3-3 1.4-1.4 1.6 1.6 3.6-3.6L16 10l-5 5Z" /></svg>
            </div>
            <div><strong>Secure team access</strong><small>Your workspace role controls the information and actions available to you.</small></div>
          </div>

          <p className="login-privacy">
            Candidate information is handled according to your organization&apos;s
            privacy policy. <Link href="/privacy">View privacy details</Link>
          </p>
        </div>

        <p className="login-candidate-link">
          Looking for a role? <Link href="/careers">Browse open positions</Link>
        </p>
      </section>
    </main>
  );
}
