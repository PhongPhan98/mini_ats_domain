"use client";

export default function LoginPage() {
  const login = () => {
    window.location.href = "http://localhost:8000/api/auth/google/login";
  };

  return (
    <div className="card" style={{ maxWidth: 560, margin: "40px auto" }}>
      <h2 style={{ marginTop: 0 }}>Welcome to Mini ATS</h2>
      <p>Please sign in with your Google account to continue.</p>
      <button style={{ width: "auto" }} onClick={login}>Sign in with Google</button>
    </div>
  );
}
