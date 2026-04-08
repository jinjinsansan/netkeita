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
      <div className="relative overflow-hidden py-14 md:py-20" style={{background:"linear-gradient(135deg,#1a1a1a 0%,#2d2200 60%,#1a1a1a 100%)"}}>
        <div className="absolute top-[-60px] right-[-60px] w-[300px] h-[300px] rounded-full border border-[#d4a017]/10 pointer-events-none" />
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
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="border border-[#e5e5e5] rounded-xl overflow-hidden animate-pulse">
                <div className="h-8 bg-[#f5e0c0]" />
                <div className="p-4 flex gap-4">
                  <div className="w-16 h-16 rounded-full bg-[#f0f0f0] shrink-0" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-4 bg-[#f0f0f0] rounded w-1/3" />
                    <div className="h-3 bg-[#f0f0f0] rounded w-2/3" />
                    <div className="h-3 bg-[#f0f0f0] rounded w-full" />
                  </div>
                </div>
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
            <p className="text-xs text-[#999] mb-4">{tipsters.length}名の公認予想家</p>
            <div className="space-y-4">
              {tipsters.map((t) => (
                <div key={t.line_user_id} className="border border-[#e0e0e0] rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  {/* Orange catchphrase badge — like netkeiba */}
                  {t.catchphrase && (
                    <div className="bg-[#e65100] px-4 py-2 text-[12px] font-bold text-white leading-tight">
                      {t.catchphrase}
                    </div>
                  )}

                  <div className="bg-white p-4">
                    <div className="flex items-start gap-4">
                      {/* Avatar */}
                      <Link href={`/tipsters/${encodeURIComponent(t.line_user_id)}`} className="shrink-0">
                        {t.picture_url ? (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={t.picture_url} alt={t.display_name}
                            className="w-16 h-16 rounded-full object-cover ring-2 ring-[#e8d99a]" />
                        ) : (
                          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#d4a017] to-[#f0c040] flex items-center justify-center text-2xl font-black text-white ring-2 ring-[#e8d99a]">
                            {t.display_name[0]}
                          </div>
                        )}
                      </Link>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Link href={`/tipsters/${encodeURIComponent(t.line_user_id)}`}
                            className="text-base font-black text-[#111] hover:text-[#d4a017] transition">
                            {t.display_name}
                          </Link>
                          <span className="text-[9px] font-bold text-[#d4a017] bg-[#fffbeb] border border-[#e8d99a] px-1.5 py-0.5 rounded-full shrink-0">公認</span>
                        </div>
                        {t.description && (
                          <p className="text-[13px] text-[#555] leading-relaxed line-clamp-2 mb-3">
                            {t.description}
                          </p>
                        )}

                        {/* SNS links */}
                        {t.sns_links && Object.values(t.sns_links).some(Boolean) && (
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {t.sns_links.x && <a href={t.sns_links.x} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[10px] font-bold text-[#555] border border-[#d0d0d0] px-2 py-0.5 rounded-full hover:border-black transition">𝕏</a>}
                            {t.sns_links.youtube && <a href={t.sns_links.youtube} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[10px] font-bold text-[#555] border border-[#d0d0d0] px-2 py-0.5 rounded-full hover:border-red-500 transition">YouTube</a>}
                            {t.sns_links.instagram && <a href={t.sns_links.instagram} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[10px] font-bold text-[#555] border border-[#d0d0d0] px-2 py-0.5 rounded-full hover:border-pink-500 transition">Instagram</a>}
                            {t.sns_links.note && <a href={t.sns_links.note} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-[10px] font-bold text-[#555] border border-[#d0d0d0] px-2 py-0.5 rounded-full hover:border-[#41c9b4] transition">note</a>}
                          </div>
                        )}

                        {/* CTA button */}
                        <Link href={`/tipsters/${encodeURIComponent(t.line_user_id)}`}
                          className="inline-flex items-center gap-1.5 bg-[#d4a017] hover:bg-[#b8860b] text-white text-xs font-bold px-4 py-2 rounded-lg transition">
                          予想を見る
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
