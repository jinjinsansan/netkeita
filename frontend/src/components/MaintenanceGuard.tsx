"use client";

import { useAuth } from "@/lib/auth-context";
import { usePathname } from "next/navigation";

const MAINTENANCE_MODE = false;
const BYPASS_PATHS = ["/login", "/auth"];

export default function MaintenanceGuard({ children }: { children: React.ReactNode }) {
  const { loading, user } = useAuth();
  const pathname = usePathname();

  if (!MAINTENANCE_MODE) return <>{children}</>;
  if (BYPASS_PATHS.some((p) => pathname.startsWith(p))) return <>{children}</>;

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-20 text-center text-[#888] text-sm">
        読み込み中...
      </div>
    );
  }

  if (user?.is_admin) return <>{children}</>;

  return (
    <div className="max-w-[960px] mx-auto px-4 py-20 text-center">
      <div className="inline-block bg-[#f5f5f5] border border-[#ddd] rounded-lg px-8 py-10">
        <div className="text-4xl mb-4">🔧</div>
        <h1 className="text-lg font-bold text-[#333] mb-2">メンテナンス中</h1>
        <p className="text-sm text-[#666] leading-relaxed">
          現在、システムの改善作業を行っています。
          <br />
          しばらくお待ちください。
        </p>
        <p className="text-[11px] text-[#999] mt-4">
          ご不便をおかけして申し訳ございません。
        </p>
      </div>
    </div>
  );
}
