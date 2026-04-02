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
      <div className="max-w-5xl mx-auto px-4 py-12 text-center text-[#888]">
        読み込み中...
      </div>
    );
  }

  if (!matrix) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12 text-center">
        <p className="text-[#888] mb-4">レースデータが見つかりません</p>
        <Link href="/" className="text-[#1E88E5] hover:underline">← レース一覧に戻る</Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <Link href="/" className="text-sm text-[#1E88E5] hover:underline mb-4 inline-block">
        ← レース一覧
      </Link>

      {/* Race header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="bg-[#E53935] text-white text-xs font-bold px-2 py-0.5 rounded">
            {matrix.race_number}R
          </span>
          <h1 className="text-lg font-bold">{matrix.race_name}</h1>
        </div>
        <p className="text-sm text-[#888]">
          {matrix.venue} / {matrix.distance} / {matrix.track_condition}
        </p>
      </div>

      <RankMatrix horses={matrix.horses} />

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-[#888]">
        {[
          { grade: "S", label: "1位", color: "#FFD700", text: "#333" },
          { grade: "A", label: "上位25%", color: "#E53935", text: "#fff" },
          { grade: "B", label: "上位50%", color: "#1E88E5", text: "#fff" },
          { grade: "C", label: "上位75%", color: "#43A047", text: "#fff" },
          { grade: "D", label: "下位25%", color: "#9E9E9E", text: "#fff" },
        ].map((r) => (
          <span key={r.grade} className="flex items-center gap-1">
            <span
              className="w-5 h-5 rounded text-center leading-5 font-bold text-[10px]"
              style={{ backgroundColor: r.color, color: r.text }}
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
