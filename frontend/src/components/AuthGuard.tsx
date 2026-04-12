"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getToken, clearToken } from "@/lib/api";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { loading, authenticated, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !authenticated) {
      const hasToken = !!getToken();
      if (!hasToken) {
        // No token at all — user is definitely logged out. Send to login.
        localStorage.setItem("nk_redirect", pathname);
        router.replace("/login");
      }
      // If hasToken but !authenticated, getMe() failed (infrastructure error).
      // Do NOT redirect — show the error state below so the user can retry
      // instead of looping through LINE login indefinitely.
    }
  }, [loading, authenticated, router, pathname]);

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center text-[#888] text-sm">
        認証確認中...
      </div>
    );
  }

  if (!authenticated) {
    const hasToken = !!getToken();
    if (hasToken) {
      // Token exists but server check failed — infrastructure/session error.
      return (
        <div className="max-w-[960px] mx-auto px-4 py-20 text-center">
          <div className="inline-block bg-[#f5f5f5] border border-[#ddd] rounded-lg px-8 py-10">
            <p className="text-base font-bold text-[#333] mb-2">セッションエラー</p>
            <p className="text-sm text-[#666] mb-6">
              認証の確認に失敗しました。<br />再度ログインしてください。
            </p>
            <button
              onClick={() => {
                clearToken();
                logout();
                localStorage.setItem("nk_redirect", pathname);
                router.replace("/login");
              }}
              className="bg-[#06C755] hover:bg-[#05b04c] text-white text-sm font-bold px-6 py-2.5 rounded-lg transition"
            >
              再ログイン
            </button>
          </div>
        </div>
      );
    }
    return null;
  }

  return <>{children}</>;
}
