import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

import { Providers } from "./providers";
import { TopBar } from "@/components/dashboard/top-bar";
import { AuthBoundary } from "@/components/dashboard/auth-boundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Glocal Ads AI",
  description: "Localization control center for media localization",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100`}>
        <Providers>
          <div className="min-h-screen">
            <TopBar />
            <main className="mx-auto max-w-6xl px-6 py-8">
              <AuthBoundary>{children}</AuthBoundary>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
