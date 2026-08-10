import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Nav } from "@/components/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinScout",
  description:
    "Public markets research agent — tool use, RAG, and agentic Q&A over free financial data sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="bg-background font-sans text-foreground antialiased">
        <Nav />
        {children}
      </body>
    </html>
  );
}
