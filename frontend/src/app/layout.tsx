import "./globals.css";
import type { ReactNode } from "react";
import NavBar from "../components/NavBar";
import ToastHost from "../components/ToastHost";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container page-enter">
          <NavBar />
          <ToastHost />
          {children}
        </div>
      </body>
    </html>
  );
}
