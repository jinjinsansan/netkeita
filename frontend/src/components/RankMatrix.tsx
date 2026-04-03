"use client";

import React, { useState, useMemo } from "react";
import type { HorseRank, RankKey } from "@/lib/types";
import { RANK_COLUMNS } from "@/lib/types";
import RankBadge from "./RankBadge";
import FrameBadge from "./FrameBadge";
import HorseDetailPanel from "./HorseDetailPanel";

interface Props {
  horses: HorseRank[];
  raceId?: string;
}

type SortMode = RankKey | "odds" | "number" | "win_prob" | "place_prob";

const FROZEN_TH: React.CSSProperties = { position: "sticky", zIndex: 10, background: "#ddd" };
const FROZEN_TD: React.CSSProperties = { position: "sticky", zIndex: 10, background: "#fff" };
const HOVER_BG = "#f0f7f0";

export default function RankMatrix({ horses, raceId }: Props) {
  const [sortKey, setSortKey] = useState<SortMode>("total");
  const [sortAsc, setSortAsc] = useState(true);
  const [expandedHorse, setExpandedHorse] = useState<number | null>(null);
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  const popularity = useMemo(() => {
    const withOdds = horses
      .map((h) => ({ num: h.horse_number, odds: h.odds ?? 999 }))
      .sort((a, b) => a.odds - b.odds);
    const map: Record<number, number> = {};
    withOdds.forEach((h, i) => { map[h.num] = i + 1; });
    return map;
  }, [horses]);

  const RANK_COLORS = ["#FFD700", "#E53935", "#1E88E5", "#43A047", "#9E9E9E"];
  const oddsRank = useMemo(() => {
    const s = horses.filter((h) => h.odds && h.odds > 0).sort((a, b) => (a.odds ?? 999) - (b.odds ?? 999));
    const m: Record<number, string> = {};
    s.slice(0, 5).forEach((h, i) => { m[h.horse_number] = RANK_COLORS[i]; });
    return m;
  }, [horses]);
  const popRank = useMemo(() => {
    const m: Record<number, string> = {};
    Object.entries(popularity).forEach(([num, rank]) => { if (rank <= 5) m[Number(num)] = RANK_COLORS[rank - 1]; });
    return m;
  }, [popularity]);
  const winRank = useMemo(() => {
    const s = horses.filter((h) => h.win_prob && h.win_prob > 0).sort((a, b) => (b.win_prob ?? 0) - (a.win_prob ?? 0));
    const m: Record<number, string> = {};
    s.slice(0, 5).forEach((h, i) => { m[h.horse_number] = RANK_COLORS[i]; });
    return m;
  }, [horses]);
  const placeRank = useMemo(() => {
    const s = horses.filter((h) => h.place_prob && h.place_prob > 0).sort((a, b) => (b.place_prob ?? 0) - (a.place_prob ?? 0));
    const m: Record<number, string> = {};
    s.slice(0, 5).forEach((h, i) => { m[h.horse_number] = RANK_COLORS[i]; });
    return m;
  }, [horses]);

  const sorted = [...horses].sort((a, b) => {
    if (sortKey === "odds") return sortAsc ? (a.odds ?? 999) - (b.odds ?? 999) : (b.odds ?? 999) - (a.odds ?? 999);
    if (sortKey === "win_prob") return sortAsc ? (b.win_prob ?? 0) - (a.win_prob ?? 0) : (a.win_prob ?? 0) - (b.win_prob ?? 0);
    if (sortKey === "place_prob") return sortAsc ? (b.place_prob ?? 0) - (a.place_prob ?? 0) : (a.place_prob ?? 0) - (b.place_prob ?? 0);
    if (sortKey === "number") return sortAsc ? a.horse_number - b.horse_number : b.horse_number - a.horse_number;
    const aVal = a.scores[sortKey as RankKey];
    const bVal = b.scores[sortKey as RankKey];
    return sortAsc ? bVal - aVal : aVal - bVal;
  });

  function handleSort(key: SortMode) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(key === "odds" || key === "number"); }
  }

  const SortHeader = ({ col, label, className }: { col: SortMode; label: string; className?: string }) => (
    <th onClick={() => handleSort(col)} className={`cursor-pointer hover:bg-[#ccc] select-none ${className || ""}`}>
      <span className={sortKey === col ? "text-[#1f7a1f] font-bold" : ""}>{label}</span>
      {sortKey === col && <span className="text-[9px] ml-0.5">{sortAsc ? "▼" : "▲"}</span>}
    </th>
  );

  const COL0_W = 36;
  const COL1_W = 36;
  const COL2_LEFT = COL0_W + COL1_W;

  const frozenThStyle = (left: number, minW?: number, extra?: React.CSSProperties): React.CSSProperties => ({
    ...FROZEN_TH, left, ...(minW ? { minWidth: minW, maxWidth: minW } : {}), ...extra,
  });
  const frozenTdStyle = (left: number, isHovered: boolean, minW?: number, extra?: React.CSSProperties): React.CSSProperties => ({
    ...FROZEN_TD, left, background: isHovered ? HOVER_BG : "#fff", ...(minW ? { minWidth: minW, maxWidth: minW } : {}), ...extra,
  });
  const shadowExtra: React.CSSProperties = { boxShadow: "2px 0 4px rgba(0,0,0,0.1)" };

  return (
    <div>
      <div className="overflow-x-auto -mx-4">
        <table className="nk-table">
          <thead>
            <tr>
              <th style={frozenThStyle(0, COL0_W)}>枠</th>
              <th className="cursor-pointer hover:bg-[#ccc] select-none" style={frozenThStyle(COL0_W, COL1_W)} onClick={() => handleSort("number")}>
                <span className={sortKey === "number" ? "text-[#1f7a1f] font-bold" : ""}>番</span>
                {sortKey === "number" && <span className="text-[9px] ml-0.5">{sortAsc ? "▼" : "▲"}</span>}
              </th>
              <th className="min-w-[72px] sm:min-w-[90px] text-left" style={frozenThStyle(COL2_LEFT, undefined, shadowExtra)}>馬名</th>
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
            {sorted.map((horse) => {
              const isHovered = hoveredRow === horse.horse_number;
              const isExpanded = expandedHorse === horse.horse_number;
              return (
                <tr
                  key={horse.horse_number}
                  className={isExpanded ? "bg-[#f0f7f0]" : ""}
                  onMouseEnter={() => setHoveredRow(horse.horse_number)}
                  onMouseLeave={() => setHoveredRow(null)}
                >
                  <td className="text-center" style={frozenTdStyle(0, isHovered || isExpanded, COL0_W)}>
                    <FrameBadge post={horse.post} />
                  </td>
                  <td className="text-center font-bold" style={frozenTdStyle(COL0_W, isHovered || isExpanded, COL1_W)}>
                    {horse.horse_number}
                  </td>
                  <td
                    className={`text-left font-medium whitespace-nowrap ${raceId ? "cursor-pointer hover:text-[#1f7a1f]" : ""}`}
                    style={frozenTdStyle(COL2_LEFT, isHovered || isExpanded, undefined, shadowExtra)}
                    onClick={() => raceId && setExpandedHorse(isExpanded ? null : horse.horse_number)}
                  >
                    <span className="inline-flex items-center gap-0.5">
                      {raceId && <span className="text-[9px] text-[#999] mr-0.5">{isExpanded ? "▼" : "▶"}</span>}
                      {horse.horse_name}
                    </span>
                  </td>
                  <td className="text-center text-[11px] text-[#444] whitespace-nowrap font-medium">{horse.jockey}</td>
                  <td className="text-center text-[12px] font-mono font-bold" style={{ color: oddsRank[horse.horse_number] || "#666" }}>
                    {horse.odds ? horse.odds.toFixed(1) : "-"}
                  </td>
                  <td className="text-center text-[12px] font-bold" style={{ color: popRank[horse.horse_number] || "#666" }}>
                    {popularity[horse.horse_number] || "-"}
                  </td>
                  <td className="text-center text-[11px] font-mono font-bold" style={{ color: winRank[horse.horse_number] || "#666" }}>
                    {horse.win_prob ? `${horse.win_prob}%` : "-"}
                  </td>
                  <td className="text-center text-[11px] font-mono font-bold" style={{ color: placeRank[horse.horse_number] || "#666" }}>
                    {horse.place_prob ? `${horse.place_prob}%` : "-"}
                  </td>
                  {RANK_COLUMNS.map((col) => (
                    <td key={col.key} className="text-center">
                      <RankBadge grade={horse.ranks[col.key]} />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {raceId && expandedHorse !== null && (
        <HorseDetailPanel
          raceId={raceId}
          horseNumber={expandedHorse}
          horseName={sorted.find((h) => h.horse_number === expandedHorse)?.horse_name || ""}
          onClose={() => setExpandedHorse(null)}
        />
      )}
    </div>
  );
}
