import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <nav className="card" style={{ display: "flex", gap: 16 }}>
            <Link href="/">Dashboard</Link>
            <Link href="/upload">Upload CV</Link>
            <Link href="/jobs">Jobs & Matching</Link>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
