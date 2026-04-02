"use client";

import { useState } from "react";
import type { HorseRank, RankKey } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";
import RankBadge from "./RankBadge";

interface Props {
  horses: HorseRank[];
}

const WAKU_BG: Record<number, string> = {
  1: "waku-bg-1",
  2: "waku-bg-2",
  3: "waku-bg-3",
  4: "waku-bg-4",
  5: "waku-bg-5",
  6: "waku-bg-6",
  7: "waku-bg-7",
  8: "waku-bg-8",
};

export default function RankMatrix({ horses }: Props) {
  const [sortKey, setSortKey] = useState<RankKey>("total");
  const [sortAsc, setSortAsc] = useState(true);

  const sorted = [...horses].sort((a, b) => {
    const aVal = a.scores[sortKey];
    const bVal = b.scores[sortKey];
    return sortAsc ? bVal - aVal : aVal - bVal;
  });

  function handleSort(key: RankKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="nk-table">
        <thead>
          <tr>
            <th className="w-8">枠</th>
            <th className="w-8">番</th>
            <th className="min-w-[100px] text-left">馬名</th>
            <th className="w-16">騎手</th>
            {RANK_COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className="cursor-pointer hover:bg-[#ddd] select-none w-[34px]"
              >
                <span className={sortKey === col.key ? "text-[#3251BC] font-bold" : ""}>
                  {col.label}
                </span>
                {sortKey === col.key && (
                  <span className="text-[9px]">{sortAsc ? "▼" : "▲"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((horse) => (
            <tr key={horse.horse_number}>
              <td className={`text-center font-bold text-xs ${WAKU_BG[horse.post] || ""}`}>
                {horse.post}
              </td>
              <td className="text-center font-bold">{horse.horse_number}</td>
              <td className="text-left font-medium whitespace-nowrap">
                {horse.horse_name}
              </td>
              <td className="text-center text-[11px] text-[#555] whitespace-nowrap">
                {horse.jockey}
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
