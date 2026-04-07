"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTipsters } from "@/lib/api";
import type { TipsterProfile } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function TipstersPage() {
  const { user } = useAuth();
  const [tipsters, setTipsters] = useState<TipsterProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTipsters().then((data) => {
      setTipsters(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="max-w-[720px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>予想家</span>
      </div>

      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-black text-[#222]">予想家</h1>
          <p className="text-[11px] text-[#888] mt-0.5">netkeita 公認の予想家が毎週のレースを分析</p>
        </div>
        {user && (
          <Link
            href="/tipsters/apply"
            className="text-xs font-bold border border-[#1f7a1f] text-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition"
          >
            予想家に申請
          </Link>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border border-[#e5e5e5] rounded-lg p-4 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-14 h-14 rounded-full bg-[#f0f0f0]" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-[#f0f0f0] rounded w-1/3" />
                  <div className="h-3 bg-[#f0f0f0] rounded w-2/3" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : tipsters.length === 0 ? (
        <div className="py-10 text-center">
          <div className="text-3xl mb-3">🏇</div>
          <div className="text-sm font-bold text-[#999]">
            まだ承認済みの予想家がいません
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {tipsters.map((t) => (
            <Link
              key={t.line_user_id}
              href={`/tipsters/${encodeURIComponent(t.line_user_id)}`}
              className="flex items-center gap-3 border border-[#d0d0d0] rounded-lg p-4 bg-white hover:border-[#1f7a1f] hover:shadow-sm transition"
            >
              {t.picture_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={t.picture_url}
                  alt={t.display_name}
                  className="w-14 h-14 rounded-full object-cover bg-[#eee] shrink-0"
                />
              ) : (
                <div className="w-14 h-14 rounded-full bg-[#e0e0e0] flex items-center justify-center text-xl font-bold text-[#888] shrink-0">
                  {t.display_name[0]}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-base font-bold text-[#222] truncate">{t.display_name}</p>
                <p className="text-xs text-[#f57c00] font-bold mt-0.5 truncate">{t.catchphrase}</p>
                {t.description && (
                  <p className="text-[11px] text-[#666] mt-1 line-clamp-2">{t.description}</p>
                )}
              </div>
              <span className="text-[#bbb] shrink-0">›</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
