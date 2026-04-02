import type { Grade } from "@/lib/types";

const COLORS: Record<Grade, { bg: string; text: string }> = {
  S: { bg: "#FFD700", text: "#333" },
  A: { bg: "#E53935", text: "#fff" },
  B: { bg: "#1E88E5", text: "#fff" },
  C: { bg: "#43A047", text: "#fff" },
  D: { bg: "#9E9E9E", text: "#fff" },
};

export default function RankBadge({ grade }: { grade: Grade }) {
  const c = COLORS[grade];
  return (
    <span
      className="inline-flex items-center justify-center w-[20px] h-[18px] rounded-sm text-[10px] font-bold leading-none"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {grade}
    </span>
  );
}
