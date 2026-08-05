import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "ProductTruth — AI Product Intelligence",
  description:
    "Turn limited product inputs into commerce-ready records where every field is confidence-scored and traceable to its source.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body style={{ background: "var(--neutral-50)", color: "var(--neutral-900)", minHeight: "100vh" }}>
        {/* Nav */}
        <nav className="nav">
          <div className="nav-inner">
            <Link href="/" className="nav-logo">
              <div className="nav-logo-badge">PT</div>
              <span className="nav-logo-text">ProductTruth</span>
            </Link>
            <div className="nav-links">
              <Link href="/" className="nav-link">Dashboard</Link>
              <Link href="/analyze" className="nav-link">Analyze</Link>
              <Link href="/review" className="nav-link">Review Queue</Link>
              <a
                href="https://github.com/Pradhyut21/Unindustry"
                target="_blank"
                rel="noopener noreferrer"
                className="nav-link"
              >
                GitHub
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
