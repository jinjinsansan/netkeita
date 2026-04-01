const FRAME_COLORS: Record<number, { bg: string; text: string; border?: string }> = {
  1: { bg: "#ffffff", text: "#333", border: "#ccc" },
  2: { bg: "#000000", text: "#fff" },
  3: { bg: "#ee0000", text: "#fff" },
  4: { bg: "#0066ff", text: "#fff" },
  5: { bg: "#ffcc00", text: "#333" },
  6: { bg: "#00aa00", text: "#fff" },
  7: { bg: "#ff8800", text: "#fff" },
  8: { bg: "#ff66cc", text: "#333" },
};

export default function FrameBadge({ post }: { post: number }) {
  const style = FRAME_COLORS[post] || FRAME_COLORS[1];
  return (
    <span
      className="inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold shrink-0"
      style={{
        backgroundColor: style.bg,
        color: style.text,
        border: style.border ? `1px solid ${style.border}` : undefined,
      }}
    >
      {post}
    </span>
  );
}
