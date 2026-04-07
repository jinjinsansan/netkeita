"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getLineLoginUrl } from "@/lib/api";

export default function HeaderLoginButton() {
  const { loading, authenticated, user, logout } = useAuth();

  if (loading) return null;

  if (authenticated && user) {
    return (
      <div className="flex items-center gap-2">
        <Link
          href="/articles"
          className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition"
        >
          記事
        </Link>
        <Link
          href="/tipsters"
          className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition"
        >
          予想家
        </Link>
        {user.is_admin && (
          <Link
            href="/admin/tipsters"
            className="text-[10px] text-[#ffd54f] hover:text-white border border-[#ffd54f]/50 px-2 py-1 rounded transition"
          >
            管理
          </Link>
        )}
        <Link
          href="/mypage"
          className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition"
        >
          マイページ
        </Link>
        <span className="text-[11px] text-[#a3c9a3] hidden sm:inline truncate max-w-[80px]">
          {user.display_name}
        </span>
        <button
          onClick={logout}
          className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition"
        >
          ログアウト
        </button>
      </div>
    );
  }

  const handleLogin = async () => {
    try {
      const { url } = await getLineLoginUrl();
      if (url) window.location.href = url;
    } catch {
      // fallback
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Link
        href="/articles"
        className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition"
      >
        記事
      </Link>
      <button
        onClick={handleLogin}
        className="flex items-center gap-1.5 bg-[#06C755] hover:bg-[#05b04c] text-white font-bold text-xs px-3 sm:px-4 py-2 rounded-lg transition"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314" />
        </svg>
        ログイン
      </button>
    </div>
  );
}
