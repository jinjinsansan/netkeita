"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMyVoteHistory } from "@/lib/api";
import type { VoteHistory } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";

export default function MyPage() {
  return (
    <AuthGuard>
      <MyPageContent />
    </AuthGuard>
  );
}

const RESULT_LABEL: Record<string, { text: string; color: string; bg: string }> = {
  hit: { text: "的中", color: "#E53935", bg: "#fce4ec" },
  miss: { text: "不的中", color: "#9E9E9E", bg: "#f5f5f5" },
  pending: { text: "結果待ち", color: "#F57C00", bg: "#fff3e0" },
};

function MyPageContent() {
  const { user } = useAuth();
  const [data, setData] = useState<VoteHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMyVoteHistory().then((d) => {
      setData(d);
      setLoading(false);
    });
  }, []);

  return (
    <div className="max-w-[960px] mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>マイページ</span>
      </div>

      {/* User header */}
      <div className="bg-[#163016] rounded-lg px-5 py-4 mb-5 flex items-center gap-3">
        <div className="w-10 h-10 bg-[#4ade80] rounded-full flex items-center justify-center shrink-0">
          <span className="text-[#163016] font-black text-sm">
            {user?.display_name?.charAt(0) || "?"}
          </span>
        </div>
        <div>
          <div className="text-white font-bold text-sm">{user?.display_name || "ユーザー"}</div>
          <div className="text-[#a3c9a3] text-[11px]">マイページ</div>
        </div>
      </div>

      {loading ? (
        <div className="py-10 text-center text-sm text-[#888] animate-pulse">
          読み込み中...
        </div>
      ) : !data || data.total_races === 0 ? (
        <div className="py-10 text-center">
          <div className="text-3xl mb-3">🗳️</div>
          <div className="text-sm font-bold text-[#999] mb-2">
            まだ投票履歴がありません
          </div>
          <div className="text-[11px] text-[#bbb] mb-4">
            レースページの「みんなの予想」から投票してみましょう
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 bg-[#1f7a1f] text-white font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-[#16611a] transition"
          >
            レース一覧へ
          </Link>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className="text-2xl font-black text-[#1f7a1f]">
                {data.total_races}
              </div>
              <div className="text-[10px] text-[#888] mt-1">投票数</div>
            </div>
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className="text-2xl font-black text-[#E53935]">
                {data.hit_rate}%
              </div>
              <div className="text-[10px] text-[#888] mt-1">的中率</div>
            </div>
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className={`text-2xl font-black ${data.roi >= 100 ? "text-[#E53935]" : "text-[#333]"}`}>
                {data.roi}%
              </div>
              <div className="text-[10px] text-[#888] mt-1">回収率</div>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-[#f8f8f8] border border-dashed border-[#d0d0d0] rounded-lg p-3 mb-5">
            <p className="text-[11px] text-[#888] leading-relaxed">
              回収率は本命馬の単勝100円購入を想定して計算しています。
              レース確定後に結果が反映されます。
            </p>
          </div>

          {/* History list */}
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-bold text-[#444]">投票履歴</span>
            <span className="text-[10px] text-[#999]">全{data.total_races}件</span>
          </div>

          <div className="space-y-2">
            {data.history.map((h) => {
              const r = RESULT_LABEL[h.result] || RESULT_LABEL.pending;
              return (
                <Link
                  key={h.race_id}
                  href={`/race/${encodeURIComponent(h.race_id)}`}
                  className="block bg-white border border-[#d0d0d0] rounded-lg p-3 hover:border-[#1f7a1f] transition shadow-sm"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[#999]">{h.date}</span>
                      <span className="text-xs font-bold text-[#333]">
                        {h.venue} {h.race_number}R
                      </span>
                      <span className="text-[11px] text-[#666]">{h.race_name}</span>
                    </div>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded"
                      style={{ color: r.color, backgroundColor: r.bg }}
                    >
                      {r.text}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#1f7a1f]">
                        {h.horse_number}番
                      </span>
                      <span className="text-sm font-bold text-[#222]">
                        {h.horse_name}
                      </span>
                    </div>
                    <div className="text-right">
                      {h.odds > 0 && (
                        <span className="text-[11px] text-[#888]">
                          {h.odds}倍
                        </span>
                      )}
                      {h.result === "hit" && (
                        <span className="text-xs font-bold text-[#E53935] ml-2">
                          +{h.payout - 100}円
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
