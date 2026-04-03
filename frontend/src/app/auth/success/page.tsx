"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import { setToken } from "@/lib/api";

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const name = searchParams.get("name");

  useEffect(() => {
    if (token) {
      setToken(token);
      const pendingPath = localStorage.getItem("nk_redirect");
      if (pendingPath) {
        localStorage.removeItem("nk_redirect");
        router.replace(pendingPath);
      } else {
        router.replace("/");
      }
    }
  }, [token, router]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="text-[#1f7a1f] text-lg font-black mb-2 animate-pulse">
          ログイン完了
        </div>
        {name && <p className="text-[#666]">{name}さん、ようこそ</p>}
        <p className="text-[#999] text-sm mt-2">リダイレクト中...</p>
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
