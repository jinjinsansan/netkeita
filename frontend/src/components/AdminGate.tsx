"use client";

import { useAuth } from "@/lib/auth-context";

export default function AdminGate({ children }: { children: React.ReactNode }) {
  const { loading, user } = useAuth();

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">
        読み込み中...
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#c62828]">
          管理者権限が必要です
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
