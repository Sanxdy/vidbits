import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "vidbits — AI Video Clipper",
  description: "Turn long videos into viral Shorts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <header className="border-b border-zinc-800 px-6 py-4">
          <div className="mx-auto flex max-w-5xl items-center gap-2">
            <span className="text-xl font-bold tracking-tight">vidbits</span>
            <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
              AI Clipper
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
