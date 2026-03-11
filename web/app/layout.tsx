import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "../components/nav";

export const metadata: Metadata = {
  title: "PropertyAdvisor",
  description: "Property intelligence MVP for suburb, advisory, and comparables workflows."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="page-shell">
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}
