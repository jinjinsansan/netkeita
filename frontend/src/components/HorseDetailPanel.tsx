"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchHorseDetail } from "@/lib/api";
import type { HorseDetail } from "@/lib/api";
import type { HorseRank, Grade } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";

type Tab = "scores" | "stable" | "recent" | "bloodline";

const TABS: { key: Tab; label: string }[] = [
  { key: "scores", label: "AIスコア" },
  { key: "stable", label: "関係者情報" },
  { key: "recent", label: "直近5走" },
  { key: "bloodline", label: "血統" },
];

export default function HorseDetailPanel({
  raceId,
  horseNumber,
  horseName,
  scores,
  ranks,
  onClose,
}: {
  raceId: string;
  horseNumber: number;
  horseName: string;
  scores: HorseRank["scores"];
  ranks: HorseRank["ranks"];
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("scores");
  const [data, setData] = useState<HorseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setLoading(true);
    setTab("scores");
    fetchHorseDetail(raceId, horseNumber).then((d) => {
      setData(d);
      setLoading(false);
    });
    requestAnimationFrame(() => setVisible(true));
  }, [raceId, horseNumber]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 250);
  }, [onClose]);

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-[60] transition-opacity duration-250"
        style={{ background: visible ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0)" }}
        onClick={handleClose}
      />
      {/* Drawer */}
      <div
        className="fixed top-0 right-0 z-[61] h-full flex flex-col bg-white shadow-lg transition-transform duration-250"
        style={{
          width: "min(85vw, 420px)",
          transform: visible ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#163016] shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="bg-[#4ade80] text-[#163016] text-[11px] font-black px-2 py-0.5 rounded shrink-0">
              {horseNumber}
            </span>
            <h2 className="text-sm font-bold text-white truncate">{horseName}</h2>
          </div>
          <button
            onClick={handleClose}
            className="text-white text-xl leading-none px-1 hover:text-[#4ade80] transition shrink-0 ml-2"
            aria-label="閉じる"
          >
            &times;
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#d0d0d0] shrink-0">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 py-2.5 text-xs font-bold text-center transition-colors ${
                tab === t.key
                  ? "text-[#1f7a1f] border-b-2 border-[#1f7a1f]"
                  : "text-[#888] hover:text-[#555]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {tab === "scores" ? (
            <ScoresTab scores={scores} ranks={ranks} />
          ) : loading ? (
            <div className="py-10 text-center text-xs text-[#888]">読み込み中...</div>
          ) : !data ? (
            <div className="py-10 text-center text-xs text-[#888]">データを取得できませんでした</div>
          ) : (
            <>
              {tab === "stable" && <StableTab data={data} />}
              {tab === "recent" && <RecentTab data={data} />}
              {tab === "bloodline" && <BloodlineTab data={data} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}

const GRADE_COLORS: Record<Grade, { bg: string; text: string }> = {
  S: { bg: "#FFD700", text: "#333" },
  A: { bg: "#E53935", text: "#fff" },
  B: { bg: "#1E88E5", text: "#fff" },
  C: { bg: "#43A047", text: "#fff" },
  D: { bg: "#9E9E9E", text: "#fff" },
};

function ScoresTab({ scores, ranks }: { scores: HorseRank["scores"]; ranks: HorseRank["ranks"] }) {
  const maxScore = Math.max(...RANK_COLUMNS.map((c) => scores[c.key]), 1);

  return (
    <div className="space-y-3">
      {RANK_COLUMNS.map((col) => {
        const score = scores[col.key];
        const grade = ranks[col.key];
        const gc = GRADE_COLORS[grade];
        const pct = Math.round((score / maxScore) * 100);
        const isTotal = col.key === "total";

        return (
          <div key={col.key} className={isTotal ? "pb-3 border-b border-[#ddd]" : ""}>
            <div className="flex items-center justify-between mb-1">
              <span className={`text-xs ${isTotal ? "font-black text-[#222]" : "font-bold text-[#444]"}`}>
                {col.label}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-[#333]">{score.toFixed(1)}</span>
                <span
                  className="inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold"
                  style={{ backgroundColor: gc.bg, color: gc.text }}
                >
                  {grade}
                </span>
              </div>
            </div>
            <div className="h-2.5 bg-[#eee] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  backgroundColor: isTotal ? "#1f7a1f" : gc.bg,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StableTab({ data }: { data: HorseDetail }) {
  const sc = data.stable_comment;
  if (!sc || (!sc.mark && !sc.comment && !sc.status)) {
    return <div className="text-xs text-[#888] text-center py-6">関係者情報はまだ公開されていません</div>;
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2.5">
        {sc.mark && (
          <span className="text-2xl font-black text-[#1f7a1f] leading-none">{sc.mark}</span>
        )}
        <div>
          <span className="font-bold text-sm text-[#222]">{data.horse_name}</span>
          {sc.status && (
            <span className="ml-2 text-[11px] bg-[#e8f5e9] text-[#1f7a1f] font-bold px-2 py-0.5 rounded">
              {sc.status}
            </span>
          )}
        </div>
      </div>
      {sc.trainer && (
        <p className="text-xs text-[#666]">{sc.trainer}</p>
      )}
      {sc.comment && (
        <div className="bg-[#f8faf8] border border-[#d0d0d0] rounded-lg p-3">
          <p className="text-[13px] text-[#333] leading-relaxed">{sc.comment}</p>
        </div>
      )}
    </div>
  );
}

function RecentTab({ data }: { data: HorseDetail }) {
  const runs = data.recent_runs;
  if (!runs || runs.length === 0) {
    return <div className="text-xs text-[#888] text-center py-6">直近走データがありません</div>;
  }
  return (
    <div className="space-y-2">
      {runs.map((r, i) => {
        const finishColor =
          r.finish === 1 ? "#FFD700" : r.finish <= 3 ? "#E53935" : r.finish <= 5 ? "#1E88E5" : "#999";
        return (
          <div key={i} className="flex items-center gap-3 py-2.5 border-b border-[#eee] last:border-0">
            <span
              className="text-xl font-black w-8 text-center shrink-0"
              style={{ color: finishColor }}
            >
              {r.finish}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-[13px]">
                <span className="font-bold text-[#222]">{r.venue}</span>
                <span className="text-[#666]">{r.distance}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#888] mt-0.5">
                <span>{r.date}</span>
                <span>{r.jockey?.trim()}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BloodlineTab({ data }: { data: HorseDetail }) {
  const bl = data.bloodline;
  if (!bl || !bl.sire) {
    return <div className="text-xs text-[#888] text-center py-6">血統データがありません</div>;
  }
  const sp = bl.sire_performance;
  const bp = bl.broodmare_performance;
  const cs = bl.sire_course_stats;

  return (
    <div className="space-y-4">
      {/* Pedigree */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#f8faf8] border border-[#d0d0d0] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-0.5">父</div>
          <div className="text-sm font-bold text-[#222]">{bl.sire}</div>
        </div>
        <div className="bg-[#f8faf8] border border-[#d0d0d0] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-0.5">母父</div>
          <div className="text-sm font-bold text-[#222]">{bl.broodmare_sire}</div>
        </div>
      </div>

      {/* Sire performance */}
      {sp && (
        <div className="border border-[#d0d0d0] rounded-lg overflow-hidden">
          <div className="bg-[#f0f7f0] px-3 py-2 flex items-center justify-between">
            <span className="text-xs font-bold text-[#333]">父 {bl.sire} の産駒成績</span>
            <span className="text-xs font-black text-[#1f7a1f]">複勝率 {sp.place_rate}%</span>
          </div>
          <div className="px-3 py-2 text-[11px] text-[#666]">
            <span>{sp.total_races}走</span>
            {sp.by_condition && sp.by_condition.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {sp.by_condition.map((c) => (
                  <span key={c.condition} className="bg-[#f5f5f5] border border-[#e8e8e8] rounded px-2 py-0.5">
                    {c.condition}: <span className="font-bold text-[#333]">{c.place_rate}%</span>
                    <span className="text-[#bbb] ml-0.5">({c.races}走)</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Broodmare sire performance */}
      {bp && (
        <div className="border border-[#d0d0d0] rounded-lg overflow-hidden">
          <div className="bg-[#f0f7f0] px-3 py-2 flex items-center justify-between">
            <span className="text-xs font-bold text-[#333]">母父 {bl.broodmare_sire} の産駒</span>
            <span className="text-xs font-black text-[#1f7a1f]">複勝率 {bp.place_rate}%</span>
          </div>
          <div className="px-3 py-2 text-[11px] text-[#666]">{bp.total_races}走</div>
        </div>
      )}

      {/* Course stats */}
      {cs && (
        <div className="border border-[#d0d0d0] rounded-lg overflow-hidden">
          <div className="bg-[#f0f7f0] px-3 py-2">
            <span className="text-xs font-bold text-[#333]">{cs.course_key} での父産駒</span>
          </div>
          <div className="px-3 py-2 flex items-center gap-4 text-xs">
            <div>
              <span className="text-[#888]">勝率</span>{" "}
              <span className="font-bold text-[#333]">{cs.win_rate}%</span>
            </div>
            <div>
              <span className="text-[#888]">複勝率</span>{" "}
              <span className="font-bold text-[#1f7a1f]">{cs.place_rate}%</span>
            </div>
            <div className="text-[#999]">({cs.total_runs}走 / {cs.wins}勝)</div>
          </div>
        </div>
      )}
    </div>
  );
}
