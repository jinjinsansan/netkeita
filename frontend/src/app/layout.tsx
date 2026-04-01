import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "netkeita - JRA全レース ランク指数",
  description: "JRA全レースの出走馬を8項目のランク指数で可視化。総合・スピード・展開・騎手・血統・近走・馬場・期待値を一目で比較。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-white text-[#333]">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}

function Header() {
  return (
    <header className="border-b border-[#e0e0e0] bg-white sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-12 flex items-center justify-between">
        <a href="/" className="text-lg font-bold text-[#333] tracking-tight">
          net<span className="text-[#E53935]">keita</span>
        </a>
        <nav className="flex items-center gap-4 text-sm text-[#888]">
          <a href="/" className="hover:text-[#333]">レース一覧</a>
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-[#e0e0e0] bg-[#f5f5f5] mt-8">
      <div className="max-w-5xl mx-auto px-4 py-4 text-center text-xs text-[#888]">
        &copy; 2026 netkeita
      </div>
    </footer>
  );
}
