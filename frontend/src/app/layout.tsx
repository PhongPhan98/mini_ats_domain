import "./globals.css";
import type { ReactNode } from "react";
import NavBar from "../components/NavBar";
import AuthGate from "../components/AuthGate";
import AppQueryProvider from "../components/QueryProvider";
import ToastHost from "../components/ToastHost";
import EmailSuggestEnhancer from "../components/EmailSuggestEnhancer";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mini ATS | Recruiting workspace",
  description: "A focused workspace for candidates, jobs and hiring pipelines.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppQueryProvider>
          <div className="app-shell page-enter">
            <NavBar />
            <ToastHost />
            <EmailSuggestEnhancer />
            <main className="app-content">
              <AuthGate>{children}</AuthGate>
            </main>
          </div>
        </AppQueryProvider>
      </body>
    </html>
  );
}
