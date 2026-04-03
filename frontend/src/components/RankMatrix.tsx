"use client";

import { useState, useMemo } from "react";
import type { HorseRank, RankKey } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";
import RankBadge from "./RankBadge";
import FrameBadge from "./FrameBadge";

interface Props {
  horses: HorseRank[];
}

type SortMode = RankKey | "odds" | "number" | "win_prob" | "place_prob";

export default function RankMatrix({ horses }: Props) {
  const [sortKey, setSortKey] = useState<SortMode>("total");
  const [sortAsc, setSortAsc] = useState(true);

  // Calculate popularity (人気) from odds
  const popularity = useMemo(() => {
    const withOdds = horses
      .map((h) => ({ num: h.horse_number, odds: h.odds ?? 999 }))
      .sort((a, b) => a.odds - b.odds);
    const map: Record<number, number> = {};
    withOdds.forEach((h, i) => {
      map[h.num] = i + 1;
    });
    return map;
  }, [horses]);

  // Top-5 rank coloring
  const RANK_COLORS = ["#FFD700", "#E53935", "#1E88E5", "#43A047", "#9E9E9E"];
  const oddsRank = useMemo(() => {
    const sorted = horses.filter((h) => h.odds && h.odds > 0)
      .sort((a, b) => (a.odds ?? 999) - (b.odds ?? 999));
    const map: Record<number, string> = {};
    sorted.slice(0, 5).forEach((h, i) => { map[h.horse_number] = RANK_COLORS[i]; });
    return map;
  }, [horses]);
  const popRank = useMemo(() => {
    const map: Record<number, string> = {};
    Object.entries(popularity).forEach(([num, rank]) => {
      if (rank <= 5) map[Number(num)] = RANK_COLORS[rank - 1];
    });
    return map;
  }, [popularity]);
  const winRank = useMemo(() => {
    const sorted = horses.filter((h) => h.win_prob && h.win_prob > 0)
      .sort((a, b) => (b.win_prob ?? 0) - (a.win_prob ?? 0));
    const map: Record<number, string> = {};
    sorted.slice(0, 5).forEach((h, i) => { map[h.horse_number] = RANK_COLORS[i]; });
    return map;
  }, [horses]);
  const placeRank = useMemo(() => {
    const sorted = horses.filter((h) => h.place_prob && h.place_prob > 0)
      .sort((a, b) => (b.place_prob ?? 0) - (a.place_prob ?? 0));
    const map: Record<number, string> = {};
    sorted.slice(0, 5).forEach((h, i) => { map[h.horse_number] = RANK_COLORS[i]; });
    return map;
  }, [horses]);

  const sorted = [...horses].sort((a, b) => {
    if (sortKey === "odds") {
      const aO = a.odds ?? 999;
      const bO = b.odds ?? 999;
      return sortAsc ? aO - bO : bO - aO;
    }
    if (sortKey === "win_prob") {
      const aW = a.win_prob ?? 0;
      const bW = b.win_prob ?? 0;
      return sortAsc ? bW - aW : aW - bW;
    }
    if (sortKey === "place_prob") {
      const aP = a.place_prob ?? 0;
      const bP = b.place_prob ?? 0;
      return sortAsc ? bP - aP : aP - bP;
    }
    if (sortKey === "number") {
      return sortAsc ? a.horse_number - b.horse_number : b.horse_number - a.horse_number;
    }
    const aVal = a.scores[sortKey as RankKey];
    const bVal = b.scores[sortKey as RankKey];
    return sortAsc ? bVal - aVal : aVal - bVal;
  });

  function handleSort(key: SortMode) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key === "odds" || key === "number");
    }
  }

  const SortHeader = ({ col, label, className }: { col: SortMode; label: string; className?: string }) => (
    <th
      onClick={() => handleSort(col)}
      className={`cursor-pointer hover:bg-[#ddd] select-none ${className || ""}`}
    >
      <span className={sortKey === col ? "text-[#3251BC] font-bold" : ""}>
        {label}
      </span>
      {sortKey === col && (
        <span className="text-[9px] ml-0.5">{sortAsc ? "▼" : "▲"}</span>
      )}
    </th>
  );

  return (
    <div className="overflow-x-auto -mx-3 px-3">
      <table className="nk-table">
        <thead>
          <tr>
            <th className="w-8 sticky left-0 z-10 bg-[#e8e8e8]">枠</th>
            <SortHeader col="number" label="番" className="w-8 sticky left-[33px] z-10 bg-[#e8e8e8]" />
            <th className="min-w-[90px] text-left sticky left-[66px] z-10 bg-[#e8e8e8]">馬名</th>
            <th className="w-14">騎手</th>
            <SortHeader col="odds" label="オッズ" className="w-12" />
            <th className="w-8">人気</th>
            <SortHeader col="win_prob" label="勝率" className="w-12" />
            <SortHeader col="place_prob" label="複勝" className="w-12" />
            {RANK_COLUMNS.map((col) => (
              <SortHeader key={col.key} col={col.key} label={col.label} className="w-[34px]" />
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((horse) => (
            <tr key={horse.horse_number}>
              <td className="text-center sticky left-0 z-10 bg-white">
                <FrameBadge post={horse.post} />
              </td>
              <td className="text-center font-bold sticky left-[33px] z-10 bg-white">{horse.horse_number}</td>
              <td className="text-left font-medium whitespace-nowrap sticky left-[66px] z-10 bg-white">
                {horse.horse_name}
              </td>
              <td className="text-center text-[11px] text-[#555] whitespace-nowrap">
                {horse.jockey}
              </td>
              <td className="text-center text-[12px] font-mono font-bold"
                style={{ color: oddsRank[horse.horse_number] || "#999" }}>
                {horse.odds ? horse.odds.toFixed(1) : "-"}
              </td>
              <td className="text-center text-[12px] font-bold"
                style={{ color: popRank[horse.horse_number] || "#999" }}>
                {popularity[horse.horse_number] || "-"}
              </td>
              <td className="text-center text-[11px] font-mono font-bold"
                style={{ color: winRank[horse.horse_number] || "#999" }}>
                {horse.win_prob ? `${horse.win_prob}%` : "-"}
              </td>
              <td className="text-center text-[11px] font-mono font-bold"
                style={{ color: placeRank[horse.horse_number] || "#999" }}>
                {horse.place_prob ? `${horse.place_prob}%` : "-"}
              </td>
              {RANK_COLUMNS.map((col) => (
                <td key={col.key} className="text-center">
                  <RankBadge grade={horse.ranks[col.key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
