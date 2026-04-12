import type { Metadata, Viewport } from "next";
import { Noto_Sans_JP } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import HeaderLoginButton from "@/components/HeaderLoginButton";
import MaintenanceGuard from "@/components/MaintenanceGuard";
import ClientFloatingChat from "@/components/ClientFloatingChat";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "netkeita - JRA全レース ランク指数 | 8項目AIデータで可視化",
  description:
    "JRA全レースの出走馬を8項目のランク指数（S〜D）で可視化。総合・スピード・展開・騎手・血統・近走・馬場・期待値を4つのAIエンジンで分析。完全無料。",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "netkeita - JRA全レース ランク指数",
    description: "8項目のAIランク指数で全馬を一目比較。完全無料のJRA競馬データサイト。",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className={`h-full antialiased ${notoSansJP.className}`}>
      <body className="min-h-full flex flex-col bg-white text-[#222]">
        <AuthProvider>
        <header className="bg-[#163016] sticky top-0 z-50 shadow-md">
          <div className="max-w-[960px] mx-auto px-4 h-14 flex items-center justify-between">
            <a href="/" className="text-xl font-black text-white tracking-tight">
              net<span className="text-[#4ade80]">keita</span>
            </a>
            <nav className="flex items-center gap-2 sm:gap-4 text-sm">
              <HeaderLoginButton />
            </nav>
          </div>
        </header>
        <main className="flex-1"><MaintenanceGuard>{children}</MaintenanceGuard></main>
        <ClientFloatingChat />
        <footer className="bg-[#163016] mt-0">
          <div className="max-w-[960px] mx-auto px-4 py-6 text-center">
            <p className="text-xs text-[#a3c9a3] mb-2">
              net<span className="text-[#4ade80] font-bold">keita</span> — JRA全レース ランク指数
            </p>
            <div className="flex items-center justify-center gap-4 mb-3">
              <a href="/terms" className="text-[11px] text-[#6b8f6b] hover:text-[#a3c9a3] transition">
                利用規約
              </a>
              <span className="text-[#2d5a2d]">|</span>
              <a href="/privacy" className="text-[11px] text-[#6b8f6b] hover:text-[#a3c9a3] transition">
                プライバシーポリシー
              </a>
              <span className="text-[#2d5a2d]">|</span>
              <a href="/tradelaw" className="text-[11px] text-[#6b8f6b] hover:text-[#a3c9a3] transition">
                特定商取引法に基づく表記
              </a>
            </div>
            <p className="text-[11px] text-[#6b8f6b]">
              &copy; 2026 netkeita. 競馬の未来を、データで。
            </p>
          </div>
        </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
