import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "netkeita - JRA全レース ランク指数 | 8項目AIデータで可視化",
  description:
    "JRA全レースの出走馬を8項目のランク指数（S〜D）で可視化。総合・スピード・展開・騎手・血統・近走・馬場・期待値を4つのAIエンジンで分析。完全無料。",
  openGraph: {
    title: "netkeita - JRA全レース ランク指数",
    description: "8項目のAIランク指数で全馬を一目比較。完全無料のJRA競馬データサイト。",
    type: "website",
  },
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
            <nav className="flex items-center gap-3 text-xs">
              <a href="#features" className="text-[#888] hover:text-[#333] hidden sm:inline">
                特長
              </a>
              <a href="#howto" className="text-[#888] hover:text-[#333] hidden sm:inline">
                使い方
              </a>
              <a
                href="#"
                className="flex items-center gap-1 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-[11px] px-3 py-1.5 rounded transition"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
                </svg>
                ログイン
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-[#c6c9d3] bg-[#f5f5f5] mt-0">
          <div className="max-w-[960px] mx-auto px-3 py-4 text-center">
            <p className="text-[11px] text-[#888] mb-1">
              net<span className="text-[#1f7a1f] font-bold">keita</span> — JRA全レース ランク指数
            </p>
            <p className="text-[10px] text-[#aaa]">
              &copy; 2026 netkeita. 競馬の未来を、データで。
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
