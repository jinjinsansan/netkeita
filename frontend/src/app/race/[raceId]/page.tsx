import { MOCK_MATRIX } from "@/lib/mock";
import RankMatrix from "@/components/RankMatrix";
import Link from "next/link";

export default async function RacePage({
  params,
}: {
  params: Promise<{ raceId: string }>;
}) {
  const { raceId } = await params;
  // TODO: fetch from API by raceId. Using mock for now.
  const matrix = MOCK_MATRIX;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Back link */}
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

      {/* Rank matrix */}
      <RankMatrix horses={matrix.horses} />

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-[#888]">
        <span className="flex items-center gap-1">
          <span className="w-5 h-5 rounded bg-[#FFD700] text-[#333] text-center leading-5 font-bold text-[10px]">S</span>
          1位
        </span>
        <span className="flex items-center gap-1">
          <span className="w-5 h-5 rounded bg-[#E53935] text-white text-center leading-5 font-bold text-[10px]">A</span>
          上位25%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-5 h-5 rounded bg-[#1E88E5] text-white text-center leading-5 font-bold text-[10px]">B</span>
          上位50%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-5 h-5 rounded bg-[#43A047] text-white text-center leading-5 font-bold text-[10px]">C</span>
          上位75%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-5 h-5 rounded bg-[#9E9E9E] text-white text-center leading-5 font-bold text-[10px]">D</span>
          下位25%
        </span>
      </div>
    </div>
  );
}
