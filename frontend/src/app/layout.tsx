import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";
import ThemeToggle from "../components/ThemeToggle";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <nav className="card nav-bar">
            <div className="nav-links">
              <Link href="/">Dashboard</Link>
              <Link href="/upload">Upload CV</Link>
              <Link href="/jobs">Jobs & Matching</Link>
            </div>
            <ThemeToggle />
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
