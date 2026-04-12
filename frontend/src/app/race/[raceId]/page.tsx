"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { fetchMatrix, fetchArticlesByRace, fetchTipsters, fetchPremiumStatus } from "@/lib/api";
import type { ArticleSummary, TipsterProfile } from "@/lib/api";

const ChatWidget = dynamic(() => import("@/components/ChatWidget"), {
  ssr: false,
  loading: () => <div className="h-[480px] bg-[#f9fafb]" />,
});
import type { RaceMatrix } from "@/lib/types";
import { pathToRaceId } from "@/lib/venue-codes";
import RankMatrix from "@/components/RankMatrix";
import MinnaVoteDrawer from "@/components/MinnaVoteDrawer";
import PredictionCard from "@/components/PredictionCard";
import AuthGuard from "@/components/AuthGuard";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function RacePage() {
  return (
    <AuthGuard>
      <RaceContent />
    </AuthGuard>
  );
}

function RaceContent() {
  const params = useParams();
  // Decode short venue code (e.g. "kws") back to Japanese ("川崎").
  // pathToRaceId is a no-op for old URLs that already contain Japanese.
  const raceId = pathToRaceId(decodeURIComponent(params.raceId as string));
  const { user } = useAuth();
  const [matrix, setMatrix] = useState<RaceMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [showVote, setShowVote] = useState(false);
  const [showPredictions, setShowPredictions] = useState(false);
  const [premiumArticles, setPremiumArticles] = useState<ArticleSummary[]>([]);
  const [tipsterMap, setTipsterMap] = useState<Record<string, TipsterProfile>>({});
  const [hasPremium, setHasPremium] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMatrix(raceId).then((data) => {
      if (cancelled) return;
      setMatrix(data);
      setLoading(false);
    });
    fetchArticlesByRace(raceId).then((articles) => {
      if (cancelled) return;
      // Only show tipster-linked articles
      setPremiumArticles(articles.filter((a) => !!a.tipster_id));
    });
    fetchTipsters().then((tipsters) => {
      if (cancelled) return;
      const m: Record<string, TipsterProfile> = {};
      for (const t of tipsters) m[t.line_user_id] = t;
      setTipsterMap(m);
    });
    if (user) {
      fetchPremiumStatus().then((p) => {
        if (!cancelled) setHasPremium(p || !!user?.is_admin);
      });
    }
    return () => { cancelled = true; };
  }, [raceId, user]);

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center text-[#888] text-sm">
        読み込み中...
      </div>
    );
  }

  if (!matrix) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center">
        <p className="text-[#555] mb-3 text-sm">レースデータが見つかりません</p>
        <Link href="/" className="text-[#1565C0] text-sm hover:underline font-bold">
          &larr; レース一覧に戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[960px] mx-auto px-4 py-4">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#666] mb-2 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>
          {matrix.venue} {matrix.race_number}R
        </span>
      </div>

      {/* Race header */}
      {(() => {
        const isLocal = matrix.is_local === true;
        const headerBg = isLocal ? "bg-[#4a148c]" : "bg-[#163016]";
        const badgeBg = isLocal ? "bg-[#ba68c8] text-[#4a148c]" : "bg-[#4ade80] text-[#163016]";
        const btnText = isLocal ? "text-[#4a148c]" : "text-[#163016]";
        const btnBg = isLocal ? "bg-[#ba68c8] hover:bg-[#ce93d8]" : "bg-[#4ade80] hover:bg-[#6ee7a0]";
        return (
          <div className="border border-[#bbb] rounded bg-white mb-3 shadow-sm">
            <div className={`flex items-center justify-between px-3 py-2.5 border-b border-[#d0d0d0] ${headerBg}`}>
              <div className="flex items-center gap-2.5">
                <span className={`${badgeBg} text-[11px] font-black px-2.5 py-0.5 rounded`}>
                  {matrix.race_number}R
                </span>
                {isLocal && (
                  <span className="bg-white/20 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">地方</span>
                )}
                <h1 className="text-sm font-bold text-white">{matrix.race_name}</h1>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setShowVote(true)}
                  className={`text-[10px] font-bold ${btnText} ${btnBg} px-2.5 py-1 rounded transition`}
                >
                  みんなの予想
                </button>
                {premiumArticles.length > 0 && (
                  <button
                    onClick={() => setShowPredictions((v) => !v)}
                    className="text-[10px] font-bold text-white bg-[#d4a017] hover:bg-[#b8860b] px-2.5 py-1 rounded transition"
                  >
                    プレミア予想 ({premiumArticles.length})
                  </button>
                )}
              </div>
            </div>
            <div className="px-3 py-2 text-[11px] text-[#444] font-medium flex flex-wrap gap-x-3">
              <span>{matrix.venue}</span>
              <span>{matrix.distance}</span>
              <span>馬場: {matrix.track_condition || "-"}</span>
              <span>{matrix.horses.length}頭</span>
            </div>
          </div>
        );
      })()}

      {/* Articles / Predictions panel */}
      {showPredictions && premiumArticles.length > 0 && (
        <div className="mb-3 border border-[#e8c84a] rounded-lg bg-[#fffdf0] p-3">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-black text-[#7c5c00]">プレミア予想</h2>
            <button
              type="button"
              onClick={() => setShowPredictions(false)}
              className="text-[11px] text-[#999] hover:text-[#444]"
            >
              閉じる ×
            </button>
          </div>
          <div className="space-y-3">
            {premiumArticles.map((p) => (
              <PredictionCard
                key={p.slug}
                prediction={p}
                tipster={p.tipster_id ? tipsterMap[p.tipster_id] : null}
                hasPremium={hasPremium}
              />
            ))}
          </div>
        </div>
      )}

      {/* Rank matrix */}
      <RankMatrix horses={matrix.horses} raceId={raceId} jockeyData={matrix.jockey_data} />

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-1.5 sm:gap-2 text-[10px] text-[#666] border-t border-[#d0d0d0] pt-2">
        <span className="font-bold text-[#333] mr-0.5 sm:mr-1">ランク:</span>
        {[
          { grade: "S", label: "1位", bg: "#FFD700", text: "#333" },
          { grade: "A", label: "上位25%", bg: "#E53935", text: "#fff" },
          { grade: "B", label: "上位50%", bg: "#1E88E5", text: "#fff" },
          { grade: "C", label: "上位75%", bg: "#43A047", text: "#fff" },
          { grade: "D", label: "下位25%", bg: "#9E9E9E", text: "#fff" },
        ].map((r) => (
          <span key={r.grade} className="flex items-center gap-1">
            <span
              className="w-4 h-4 rounded-sm text-center leading-4 font-bold text-[9px] inline-block"
              style={{ backgroundColor: r.bg, color: r.text }}
            >
              {r.grade}
            </span>
            {r.label}
          </span>
        ))}
      </div>
      <p className="text-[10px] text-[#888] mt-1">
        ※ 各項目は出走馬全頭の相対順位でランク付け。ヘッダーをタップでソート切替。
      </p>

      {/* Chat */}
      <div className="mt-6 border border-[#e5e7eb] rounded-xl overflow-hidden h-[480px]">
        <ChatWidget
          defaultChannel={matrix.is_local ? "nar" : "jra"}
          embedded={true}
        />
      </div>

      {/* Minna-no-Yosou vote drawer */}
      {showVote && (
        <MinnaVoteDrawer
          raceId={raceId}
          horses={matrix.horses}
          onClose={() => setShowVote(false)}
        />
      )}
    </div>
  );
}
