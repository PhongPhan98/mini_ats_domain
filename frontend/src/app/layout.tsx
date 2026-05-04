import "./globals.css";
import type { ReactNode } from "react";
import NavBar from "../components/NavBar";
import AuthGate from "../components/AuthGate";
import AppQueryProvider from "../components/QueryProvider";
import ToastHost from "../components/ToastHost";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container page-enter">
          <NavBar />
          <ToastHost />
          <AuthGate>{children}</AuthGate>
        </div>
      </body>
    </html>
  );
}
