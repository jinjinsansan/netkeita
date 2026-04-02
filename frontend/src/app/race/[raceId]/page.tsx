"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchMatrix } from "@/lib/api";
import type { RaceMatrix } from "@/lib/types";
import RankMatrix from "@/components/RankMatrix";
import Link from "next/link";

export default function RacePage() {
  const params = useParams();
  const raceId = decodeURIComponent(params.raceId as string);
  const [matrix, setMatrix] = useState<RaceMatrix | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMatrix(raceId).then((data) => {
      setMatrix(data);
      setLoading(false);
    });
  }, [raceId]);

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-3 py-10 text-center text-[#888] text-xs">
        読み込み中...
      </div>
    );
  }

  if (!matrix) {
    return (
      <div className="max-w-[960px] mx-auto px-3 py-10 text-center">
        <p className="text-[#888] mb-3 text-xs">レースデータが見つかりません</p>
        <Link href="/" className="text-[#1E88E5] text-xs hover:underline">
          &larr; レース一覧に戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[960px] mx-auto px-3 py-4">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#888] mb-2">
        <Link href="/" className="text-[#1E88E5] hover:underline">
          レース一覧
        </Link>
        <span className="mx-1">&gt;</span>
        <span>
          {matrix.venue} {matrix.race_number}R
        </span>
      </div>

      {/* Race header (netkeiba style) */}
      <div className="border border-[#c6c9d3] rounded bg-white mb-3">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[#e0e0e0] bg-[#f5f5f5]">
          <span className="bg-[#1f7a1f] text-white text-[11px] font-bold px-2 py-0.5 rounded">
            {matrix.race_number}R
          </span>
          <h1 className="text-sm font-bold">{matrix.race_name}</h1>
        </div>
        <div className="px-3 py-1.5 text-[11px] text-[#555] flex flex-wrap gap-x-3">
          <span>{matrix.venue}</span>
          <span>{matrix.distance}</span>
          <span>馬場: {matrix.track_condition || "-"}</span>
          <span>{matrix.horses.length}頭</span>
        </div>
      </div>

      {/* Rank matrix */}
      <RankMatrix horses={matrix.horses} />

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-2 text-[10px] text-[#888] border-t border-[#e0e0e0] pt-2">
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
    </div>
  );
}
