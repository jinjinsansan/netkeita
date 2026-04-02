import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "netkeita - JRA全レース ランク指数",
  description:
    "JRA全レースの出走馬を8項目のランク指数で可視化。総合・スピード・展開・騎手・血統・近走・馬場・期待値を一目で比較。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-white text-[#333]">
        <header className="border-b border-[#c6c9d3] bg-white sticky top-0 z-50">
          <div className="max-w-[960px] mx-auto px-3 h-11 flex items-center justify-between">
            <a href="/" className="text-base font-bold text-[#333] tracking-tight">
              net<span className="text-[#1f7a1f]">keita</span>
            </a>
            <nav className="flex items-center gap-4 text-xs text-[#888]">
              <a href="/" className="hover:text-[#333]">
                レース一覧
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-[#c6c9d3] bg-[#f5f5f5] mt-6">
          <div className="max-w-[960px] mx-auto px-3 py-3 text-center text-[10px] text-[#888]">
            &copy; 2026 netkeita
          </div>
        </footer>
      </body>
    </html>
  );
}
