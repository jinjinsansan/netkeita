"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getLineLoginUrl, isLoggedIn } from "@/lib/api";

const CALLBACK_ERRORS: Record<string, string> = {
  cancelled: "LINEログインがキャンセルされました。",
  failed: "LINE認証に失敗しました。もう一度お試しください。",
  network: "サーバーとの通信に失敗しました。しばらく待ってから再試行してください。",
  session: "セッションの作成に失敗しました。もう一度お試しください。",
};

function LoginContent() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/");
    const errorCode = searchParams.get("error");
    if (errorCode) setError(CALLBACK_ERRORS[errorCode] ?? "ログインに失敗しました。もう一度お試しください。");
  }, [router, searchParams]);

  const startLineLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const { url } = await getLineLoginUrl();
      if (!url) {
        setError("LINEログインの開始に失敗しました");
        return;
      }
      window.location.href = url;
    } catch {
      setError("通信エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-black">
            net<span className="text-[#4ade80]">keita</span>
          </h1>
          <p className="text-[#888] text-sm mt-1">JRA全レース ランク指数</p>
        </div>

        <div className="bg-white border border-[#d0d0d0] rounded-xl p-6 shadow-sm">
          <h2 className="text-base font-bold text-center mb-2">ログイン</h2>
          <p className="text-sm text-[#888] text-center mb-6">
            レースデータの閲覧にはLINEログインが必要です。
            <br />
            ログインと同時にLINE公式アカウントを友だち追加できます。
          </p>

          {error && (
            <p className="text-sm text-red-500 text-center mb-4">{error}</p>
          )}

          <button
            onClick={startLineLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl font-bold text-white text-sm transition hover:opacity-90 active:scale-[0.98] disabled:opacity-40"
            style={{ background: "#06C755" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
            </svg>
            {loading ? "準備中..." : "LINEでログイン"}
          </button>
        </div>

        <div className="text-center mt-5">
          <a href="/" className="text-xs text-[#999] hover:text-[#555] transition">
            &larr; トップページに戻る
          </a>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-[70vh] flex items-center justify-center text-[#888] text-sm">読み込み中...</div>}>
      <LoginContent />
    </Suspense>
  );
}
