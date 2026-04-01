"use client";

import { useState } from "react";
import type { HorseRank, RankKey } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";
import RankBadge from "./RankBadge";
import FrameBadge from "./FrameBadge";

interface Props {
  horses: HorseRank[];
}

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
    <div className="relative overflow-x-auto border border-[#e0e0e0] rounded-lg">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#f5f5f5] border-b border-[#e0e0e0]">
            <th className="sticky left-0 z-10 bg-[#f5f5f5] px-3 py-2 text-left whitespace-nowrap min-w-[140px]">
              馬名
            </th>
            {RANK_COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className="px-2 py-2 text-center cursor-pointer hover:bg-[#eee] whitespace-nowrap min-w-[56px] select-none"
              >
                <span className={sortKey === col.key ? "text-[#E53935] font-bold" : "text-[#555]"}>
                  {col.label}
                </span>
                {sortKey === col.key && (
                  <span className="ml-0.5 text-[10px]">{sortAsc ? "▼" : "▲"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((horse, i) => (
            <tr
              key={horse.horse_number}
              className={`border-b border-[#f0f0f0] ${i % 2 === 0 ? "bg-white" : "bg-[#fafafa]"}`}
            >
              <td className="sticky left-0 z-10 px-3 py-2 whitespace-nowrap bg-inherit">
                <div className="flex items-center gap-2">
                  <FrameBadge post={horse.post} />
                  <span className="font-bold text-sm">{horse.horse_number}</span>
                  <a
                    href={`/horse/${horse.horse_number}`}
                    className="text-sm font-medium hover:text-[#1E88E5] hover:underline truncate max-w-[90px]"
                  >
                    {horse.horse_name}
                  </a>
                </div>
              </td>
              {RANK_COLUMNS.map((col) => (
                <td key={col.key} className="px-2 py-2 text-center">
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
