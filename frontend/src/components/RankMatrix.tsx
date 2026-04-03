"use client";

import { useState, useMemo } from "react";
import type { HorseRank, RankKey } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";
import RankBadge from "./RankBadge";
import FrameBadge from "./FrameBadge";

interface Props {
  horses: HorseRank[];
}

type SortMode = RankKey | "odds" | "number";

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

  const sorted = [...horses].sort((a, b) => {
    if (sortKey === "odds") {
      const aO = a.odds ?? 999;
      const bO = b.odds ?? 999;
      return sortAsc ? aO - bO : bO - aO;
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
              <td className="text-center text-[12px] font-mono text-[#333]">
                {horse.odds ? horse.odds.toFixed(1) : "-"}
              </td>
              <td className="text-center text-[12px] font-bold">
                <span className={`${popularity[horse.horse_number] <= 3 ? "text-[#E53935]" : "text-[#555]"}`}>
                  {popularity[horse.horse_number] || "-"}
                </span>
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
