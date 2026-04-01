import type { Grade } from "@/lib/types";

const GRADE_STYLES: Record<Grade, string> = {
  S: "bg-[#FFD700] text-[#333] font-bold",
  A: "bg-[#E53935] text-white",
  B: "bg-[#1E88E5] text-white",
  C: "bg-[#43A047] text-white",
  D: "bg-[#9E9E9E] text-white",
};

export default function RankBadge({ grade }: { grade: Grade }) {
  return (
    <span
      className={`inline-flex items-center justify-center w-8 h-8 rounded text-sm font-semibold ${GRADE_STYLES[grade]}`}
    >
      {grade}
    </span>
  );
}
