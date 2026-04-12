"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import { setToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refresh, loading, authenticated } = useAuth();
  const token = searchParams.get("token");
  const name = searchParams.get("name");

  // Tracks whether we've saved the token and triggered the auth check.
  // Using state (not ref) so that React batches setAuthStarted(true) with
  // the setLoading(true) triggered by refresh(), ensuring the second effect
  // always sees loading=true when authStarted first becomes true.
  const [authStarted, setAuthStarted] = useState(false);

  // Step 1: Save the token to localStorage and trigger getMe().
  useEffect(() => {
    if (!token || authStarted) return;
    setToken(token);
    setAuthStarted(true); // batched with setLoading(true) from refresh() below
    refresh();
  }, [token, refresh, authStarted]);

  // Step 2: Navigate only AFTER the auth check has fully settled.
  // This prevents React concurrent-mode from rendering the destination page
  // before authenticated=true is committed, which caused the login loop.
  useEffect(() => {
    if (!authStarted || loading) return; // not started yet, or getMe() still in flight
    if (authenticated) {
      const pendingPath = localStorage.getItem("nk_redirect");
      if (pendingPath) {
        localStorage.removeItem("nk_redirect");
        router.replace(pendingPath);
      } else {
        router.replace("/");
      }
    } else {
      // getMe() returned authenticated:false — session wasn't persisted in Redis
      router.replace("/login?error=session");
    }
  }, [authStarted, loading, authenticated, router]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="text-[#1f7a1f] text-lg font-black mb-2 animate-pulse">
          ログイン完了
        </div>
        {name && <p className="text-[#666]">{name}さん、ようこそ</p>}
        <p className="text-[#999] text-sm mt-2">認証確認中...</p>
      </div>
    </div>
  );
}

export default function AuthSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <div className="text-[#1f7a1f] animate-pulse">処理中...</div>
        </div>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}
