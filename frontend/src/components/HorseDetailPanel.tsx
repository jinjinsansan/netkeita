"use client";

import { useState, useEffect } from "react";
import { fetchHorseDetail } from "@/lib/api";
import type { HorseDetail } from "@/lib/api";

type Tab = "stable" | "recent" | "bloodline";

export default function HorseDetailPanel({ raceId, horseNumber, horseName }: {
  raceId: string;
  horseNumber: number;
  horseName: string;
}) {
  const [tab, setTab] = useState<Tab>("stable");
  const [data, setData] = useState<HorseDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchHorseDetail(raceId, horseNumber).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [raceId, horseNumber]);

  const TABS: { key: Tab; label: string }[] = [
    { key: "stable", label: "関係者情報" },
    { key: "recent", label: "直近5走" },
    { key: "bloodline", label: "血統" },
  ];

  if (loading) {
    return (
      <div className="py-4 text-center text-xs text-[#888]">読み込み中...</div>
    );
  }
  if (!data) {
    return (
      <div className="py-4 text-center text-xs text-[#888]">データを取得できませんでした</div>
    );
  }

  return (
    <div className="bg-[#fafafa] border-t border-[#d0d0d0]">
      <div className="flex border-b border-[#d0d0d0]">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 py-2 text-xs font-bold text-center transition ${
              tab === t.key
                ? "bg-[#163016] text-white"
                : "bg-[#eee] text-[#555] hover:bg-[#ddd]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-3">
        {tab === "stable" && <StableTab data={data} />}
        {tab === "recent" && <RecentTab data={data} />}
        {tab === "bloodline" && <BloodlineTab data={data} />}
      </div>
    </div>
  );
}

function StableTab({ data }: { data: HorseDetail }) {
  const sc = data.stable_comment;
  if (!sc || (!sc.mark && !sc.comment && !sc.status)) {
    return <div className="text-xs text-[#888] text-center py-2">関係者情報はまだ公開されていません</div>;
  }
  return (
    <div className="text-sm space-y-1.5">
      <div className="flex items-center gap-2">
        {sc.mark && (
          <span className="text-lg font-black text-[#1f7a1f]">{sc.mark}</span>
        )}
        <span className="font-bold text-[#222]">{data.horse_name}</span>
        {sc.status && (
          <span className="text-xs bg-[#e8f5e9] text-[#1f7a1f] font-bold px-2 py-0.5 rounded">
            {sc.status}
          </span>
        )}
      </div>
      {sc.trainer && (
        <p className="text-xs text-[#666]">{sc.trainer}</p>
      )}
      {sc.comment && (
        <p className="text-xs text-[#333] leading-relaxed bg-white border border-[#ddd] rounded p-2">
          {sc.comment}
        </p>
      )}
    </div>
  );
}

function RecentTab({ data }: { data: HorseDetail }) {
  const runs = data.recent_runs;
  if (!runs || runs.length === 0) {
    return <div className="text-xs text-[#888] text-center py-2">直近走データがありません</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-[#ddd] text-[#222]">
            <th className="px-2 py-1.5 text-left font-bold">日付</th>
            <th className="px-2 py-1.5 text-left font-bold">競馬場</th>
            <th className="px-2 py-1.5 text-center font-bold">距離</th>
            <th className="px-2 py-1.5 text-center font-bold">着順</th>
            <th className="px-2 py-1.5 text-left font-bold">騎手</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => {
            const finishColor = r.finish === 1 ? "#FFD700" : r.finish <= 3 ? "#E53935" : r.finish <= 5 ? "#1E88E5" : "#666";
            return (
              <tr key={i} className="border-b border-[#e8e8e8]">
                <td className="px-2 py-1.5 text-[#444]">{r.date}</td>
                <td className="px-2 py-1.5 text-[#444]">{r.venue}</td>
                <td className="px-2 py-1.5 text-center text-[#444]">{r.distance}</td>
                <td className="px-2 py-1.5 text-center font-black text-base" style={{ color: finishColor }}>
                  {r.finish}
                </td>
                <td className="px-2 py-1.5 text-[#444]">{r.jockey?.trim()}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BloodlineTab({ data }: { data: HorseDetail }) {
  const bl = data.bloodline;
  if (!bl || !bl.sire) {
    return <div className="text-xs text-[#888] text-center py-2">血統データがありません</div>;
  }
  const sp = bl.sire_performance;
  const bp = bl.broodmare_performance;
  const cs = bl.sire_course_stats;

  return (
    <div className="text-xs space-y-3">
      <div className="flex gap-4">
        <div>
          <span className="text-[#888]">父:</span>{" "}
          <span className="font-bold text-[#222]">{bl.sire}</span>
        </div>
        <div>
          <span className="text-[#888]">母父:</span>{" "}
          <span className="font-bold text-[#222]">{bl.broodmare_sire}</span>
        </div>
      </div>

      {sp && (
        <div className="bg-white border border-[#ddd] rounded p-2">
          <h4 className="font-bold text-[#333] mb-1">
            父 {bl.sire} の産駒成績
            <span className="ml-2 text-[#1f7a1f] font-black">複勝率 {sp.place_rate}%</span>
            <span className="ml-1 text-[#888] font-normal">({sp.total_races}走)</span>
          </h4>
          {sp.by_condition && sp.by_condition.length > 0 && (
            <div className="flex gap-2 mt-1 flex-wrap">
              {sp.by_condition.map((c) => (
                <span key={c.condition} className="bg-[#f5f5f5] border border-[#ddd] rounded px-2 py-0.5">
                  {c.condition}: <span className="font-bold">{c.place_rate}%</span>
                  <span className="text-[#aaa] ml-0.5">({c.races}走)</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {bp && (
        <div className="bg-white border border-[#ddd] rounded p-2">
          <h4 className="font-bold text-[#333]">
            母父 {bl.broodmare_sire} の産駒成績
            <span className="ml-2 text-[#1f7a1f] font-black">複勝率 {bp.place_rate}%</span>
            <span className="ml-1 text-[#888] font-normal">({bp.total_races}走)</span>
          </h4>
        </div>
      )}

      {cs && (
        <div className="bg-white border border-[#ddd] rounded p-2">
          <h4 className="font-bold text-[#333]">
            {cs.course_key} での父産駒
          </h4>
          <div className="flex gap-3 mt-1">
            <span>勝率: <span className="font-bold">{cs.win_rate}%</span></span>
            <span>複勝率: <span className="font-bold text-[#1f7a1f]">{cs.place_rate}%</span></span>
            <span className="text-[#888]">({cs.total_runs}走 / {cs.wins}勝)</span>
          </div>
        </div>
      )}
    </div>
  );
}
