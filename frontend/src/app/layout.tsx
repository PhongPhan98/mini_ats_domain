import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";
import ThemeToggle from "../components/ThemeToggle";
import CompactModeToggle from "../components/CompactModeToggle";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container page-enter">
          <nav className="card nav-bar">
            <div className="nav-links">
              <Link href="/">Dashboard</Link>
              <Link href="/upload">Upload CV</Link>
              <Link href="/jobs">Jobs & Matching</Link>
            </div>
            <div className="nav-actions">
              <CompactModeToggle />
              <ThemeToggle />
            </div>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
