"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getLineLoginUrl } from "@/lib/api";

export default function HeaderLoginButton() {
  const { loading, authenticated, user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 外側クリックで閉じる
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (loading) return null;

  if (authenticated && user) {
    const hasPowerLinks = user.is_admin || user.is_tipster;

    // 一般ユーザーはドロップダウン不要 — シンプル表示
    if (!hasPowerLinks) {
      return (
        <div className="flex items-center gap-2">
          <Link href="/mypage" className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition">
            マイページ
          </Link>
          <span className="text-[11px] text-[#a3c9a3] hidden sm:inline truncate max-w-[80px]">{user.display_name}</span>
          <button onClick={logout} className="text-[10px] text-[#a3c9a3] hover:text-white border border-[#a3c9a3]/30 px-2 py-1 rounded transition">
            ログアウト
          </button>
        </div>
      );
    }

    // 管理者 / 予想家 — アバタードロップダウン
    return (
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 text-[11px] text-[#a3c9a3] hover:text-white px-2 py-1 rounded transition select-none"
        >
          {user.picture_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={user.picture_url} alt="" className="w-6 h-6 rounded-full object-cover" />
          ) : (
            <span className="w-6 h-6 rounded-full bg-[#4ade80] flex items-center justify-center text-[10px] font-black text-[#163016]">
              {user.display_name[0]}
            </span>
          )}
          <span className="hidden sm:inline truncate max-w-[72px]">{user.display_name}</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" className={`transition-transform ${open ? "rotate-180" : ""}`}>
            <path d="M1 3l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {open && (
          <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-[#d0d0d0] rounded-lg shadow-xl z-50 overflow-hidden">
            {/* 予想家メニュー */}
            {(user.is_tipster || user.is_admin) && (
              <>
                <div className="px-3 py-1.5 text-[9px] font-bold text-[#999] uppercase tracking-wider bg-[#f9f9f9]">予想家</div>
                <Link href="/tipsters/dashboard" onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-[#222] hover:bg-[#f0f7f0] transition">
                  ダッシュボード
                </Link>
                <Link href="/predictions/new" onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-[#222] hover:bg-[#f0f7f0] transition">
                  予想を投稿
                </Link>
              </>
            )}
            {/* 管理者メニュー */}
            {user.is_admin && (
              <>
                <div className="px-3 py-1.5 text-[9px] font-bold text-[#999] uppercase tracking-wider bg-[#f9f9f9]">管理者</div>
                <Link href="/articles" onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-[#222] hover:bg-[#f0f7f0] transition">
                  記事
                </Link>
                <Link href="/tipsters" onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-[#222] hover:bg-[#f0f7f0] transition">
                  予想家一覧
                </Link>
                <Link href="/admin/tipsters" onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-[#ffd54f] font-bold hover:bg-[#fffde7] transition">
                  管理
                </Link>
              </>
            )}
            {/* 共通 */}
            <div className="border-t border-[#e5e5e5]">
              <Link href="/mypage" onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-[#222] hover:bg-[#f5f5f5] transition">
                マイページ
              </Link>
              <button onClick={() => { logout(); setOpen(false); }}
                className="w-full text-left flex items-center gap-2 px-3 py-2 text-xs text-[#c62828] hover:bg-[#fdecea] transition">
                ログアウト
              </button>
            </div>
          </div>
        )}
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
