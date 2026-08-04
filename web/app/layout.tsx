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
      <body className="bg-zinc-950 text-zinc-100 min-h-screen antialiased">
        {/* Nav */}
        <nav className="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-xs font-bold">
                PT
              </div>
              <span className="font-semibold text-zinc-100 group-hover:text-white transition-colors">
                ProductTruth
              </span>
              <span className="text-xs text-zinc-500 border border-zinc-700 rounded px-1.5 py-0.5 font-mono">
                v0.1
              </span>
            </Link>
            <div className="flex items-center gap-6 text-sm">
              <Link
                href="/"
                className="text-zinc-400 hover:text-zinc-100 transition-colors"
              >
                Analyze
              </Link>
              <Link
                href="/review"
                className="text-zinc-400 hover:text-zinc-100 transition-colors"
              >
                Review Queue
              </Link>
              <a
                href="https://github.com/Pradhyut21/Unindustry"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-400 hover:text-zinc-100 transition-colors"
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
