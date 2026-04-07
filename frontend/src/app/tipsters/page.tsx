"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTipsters } from "@/lib/api";
import type { TipsterProfile } from "@/lib/api";

export default function TipstersPage() {
  const [tipsters, setTipsters] = useState<TipsterProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTipsters().then((data) => {
      setTipsters(data);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      {/* Hero */}
      <div className="relative overflow-hidden py-14 md:py-20" style={{background: "linear-gradient(135deg, #1a1a1a 0%, #2d2200 60%, #1a1a1a 100%)"}}>
        {/* decorative rings */}
        <div className="absolute top-[-60px] right-[-60px] w-[300px] h-[300px] rounded-full border border-[#d4a017]/10 pointer-events-none" />
        <div className="absolute top-[-30px] right-[-30px] w-[200px] h-[200px] rounded-full border border-[#d4a017]/15 pointer-events-none" />
        <div className="absolute bottom-[-80px] left-[-40px] w-[250px] h-[250px] rounded-full border border-[#d4a017]/10 pointer-events-none" />

        <div className="relative max-w-[900px] mx-auto px-5 text-center">
          <span className="inline-flex items-center gap-1.5 bg-[#d4a017]/20 text-[#ffd54f] text-xs font-bold px-4 py-1.5 rounded-full mb-5 tracking-wider">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>
            OFFICIAL CERTIFIED
          </span>
          <h1 className="text-3xl md:text-4xl font-black text-white mb-3 tracking-tight">
            netkeita<span className="text-[#ffd54f]">公認</span>予想家
          </h1>
          <p className="text-sm md:text-base text-[#aaa] max-w-[500px] mx-auto leading-relaxed">
            厳しい審査を通過した予想家だけが公認バッジを取得。<br className="hidden sm:inline" />
            データに基づいた本格的な予想をお届けします。
          </p>
        </div>
      </div>

      {/* Breadcrumb */}
      <div className="max-w-[900px] mx-auto px-5 pt-5 pb-1">
        <div className="text-[11px] text-[#666] font-medium">
          <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
          <span className="mx-1 text-[#999]">&gt;</span>
          <span>公認予想家</span>
        </div>
      </div>

      <div className="max-w-[900px] mx-auto px-5 py-6">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="border border-[#e5e5e5] rounded-2xl p-5 animate-pulse">
                <div className="flex items-center gap-4 mb-3">
                  <div className="w-16 h-16 rounded-full bg-[#f0f0f0] shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-[#f0f0f0] rounded w-1/2" />
                    <div className="h-3 bg-[#f0f0f0] rounded w-3/4" />
                  </div>
                </div>
                <div className="h-3 bg-[#f0f0f0] rounded w-full mb-1.5" />
                <div className="h-3 bg-[#f0f0f0] rounded w-4/5" />
              </div>
            ))}
          </div>
        ) : tipsters.length === 0 ? (
          <div className="py-20 text-center">
            <div className="w-16 h-16 rounded-full bg-[#f5f0e0] flex items-center justify-center mx-auto mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#d4a017" strokeWidth="1.5"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>
            </div>
            <p className="text-sm font-bold text-[#888] mb-1">まだ公認予想家がいません</p>
            <p className="text-xs text-[#aaa]">しばらくお待ちください</p>
          </div>
        ) : (
          <>
            <p className="text-xs text-[#999] mb-5">{tipsters.length}名の公認予想家</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {tipsters.map((t) => (
                <Link
                  key={t.line_user_id}
                  href={`/tipsters/${encodeURIComponent(t.line_user_id)}`}
                  className="group relative flex flex-col bg-white border border-[#e5e5e5] rounded-2xl overflow-hidden hover:border-[#d4a017] hover:shadow-xl transition-all duration-200"
                >
                  {/* Top accent bar */}
                  <div className="h-1 bg-gradient-to-r from-[#d4a017] via-[#f0c040] to-[#d4a017]" />

                  <div className="p-5">
                    {/* Avatar + name row */}
                    <div className="flex items-start gap-4 mb-3">
                      <div className="relative shrink-0">
                        {t.picture_url ? (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={t.picture_url}
                            alt={t.display_name}
                            className="w-16 h-16 rounded-full object-cover ring-[3px] ring-[#e8d99a] group-hover:ring-[#d4a017] transition"
                          />
                        ) : (
                          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#d4a017] to-[#f0c040] flex items-center justify-center text-2xl font-black text-white ring-[3px] ring-[#e8d99a] group-hover:ring-[#d4a017] transition">
                            {t.display_name[0]}
                          </div>
                        )}
                        {/* badge */}
                        <span className="absolute -bottom-0.5 -right-0.5 w-6 h-6 bg-[#d4a017] rounded-full flex items-center justify-center shadow">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="white"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>
                        </span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-0.5">
                          <p className="text-base font-black text-[#111] truncate group-hover:text-[#b8860b] transition">
                            {t.display_name}
                          </p>
                          <span className="shrink-0 text-[9px] font-bold text-[#d4a017] bg-[#fffbeb] border border-[#e8d99a] px-1.5 py-0.5 rounded-full">
                            公認
                          </span>
                        </div>
                        {t.catchphrase && (
                          <p className="text-xs text-[#b8860b] font-bold leading-snug line-clamp-2">
                            {t.catchphrase}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Description */}
                    {t.description && (
                      <p className="text-[12px] text-[#555] leading-relaxed line-clamp-3 border-t border-[#f5f5f5] pt-3">
                        {t.description}
                      </p>
                    )}

                    {/* CTA */}
                    <div className="flex items-center justify-end mt-3">
                      <span className="text-xs font-bold text-[#d4a017] group-hover:underline flex items-center gap-1">
                        予想を見る
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
