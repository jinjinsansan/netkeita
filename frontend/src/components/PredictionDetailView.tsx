"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import type { Article, TipsterProfile } from "@/lib/api";
import { formatDate } from "@/lib/format";
import ShareButton from "@/components/ShareButton";
import { SITE_URL } from "@/lib/site";
import { raceIdToPath } from "@/lib/venue-codes";

const MARK_STYLE: Record<string, { label: string; color: string; bg: string }> = {
  "◎": { label: "◎", color: "#c62828", bg: "#fff" },
  "○": { label: "○", color: "#c62828", bg: "#fff" },
  "▲": { label: "▲", color: "#1565c0", bg: "#fff" },
  "△": { label: "△", color: "#1565c0", bg: "#fff" },
  "☆": { label: "☆", color: "#f57c00", bg: "#fff" },
  "✖": { label: "✖", color: "#888", bg: "#fff" },
};

const WAKU_BG: Record<number, string> = {
  1: "bg-white text-[#333] border border-[#ccc]",
  2: "bg-black text-white",
  3: "bg-[#ee0000] text-white",
  4: "bg-[#0066ff] text-white",
  5: "bg-[#ffcc00] text-[#333]",
  6: "bg-[#00aa00] text-white",
  7: "bg-[#ff8800] text-white",
  8: "bg-[#ff66cc] text-[#333]",
};

interface Mark {
  horseNumber: number;
  horseName: string;
  mark: string;
  popularity?: number;
  post?: number;
}

function parseMarks(body: string): Mark[] {
  const lines = body.split("\n");
  const marks: Mark[] = [];
  const MARK_PATTERN = /^([◎○▲△☆✖])\s*(\d+)[.\s　]+(.+?)(?:\s*[\(（](\d+)人気[\)）])?$/;
  for (const line of lines) {
    const m = line.trim().match(MARK_PATTERN);
    if (m) {
      marks.push({
        mark: m[1],
        horseNumber: parseInt(m[2], 10),
        horseName: m[3].trim(),
        popularity: m[4] ? parseInt(m[4], 10) : undefined,
      });
    }
  }
  return marks;
}

interface PredictionDetailViewProps {
  article: Article;
  tipster?: TipsterProfile | null;
  hasPremium?: boolean;
  isAdmin?: boolean;
  deleting?: boolean;
  onDeleteRequest?: () => void;
}

export default function PredictionDetailView({ article, tipster, hasPremium, isAdmin, deleting, onDeleteRequest }: PredictionDetailViewProps) {
  const slug = article.slug;
  const isPremium = !!article.is_premium;
  const canRead = !isPremium || hasPremium;

  const marks = canRead ? parseMarks(article.body) : [];
  const hasStructuredMarks = marks.length >= 2;

  // Split body into marks section and rest (buy tickets etc.)
  // restBody は「印ブロックとしてカード化した部分を除いた残り」を指す。
  // hasStructuredMarks=false のときは印カードを出さず、本文は下段の fallback
  // ブロック側 (article.body をそのまま) で描画するので、ここは空にしておく。
  // 以前は article.body をフォールバックにしていたため、fallback ブロックと
  // 二重に描画されるバグになっていた。
  const bodyLines = article.body.split("\n");
  const MARK_RE = /^[◎○▲△☆✖]/;
  const firstMarkIdx = bodyLines.findIndex((l) => MARK_RE.test(l.trim()));
  const lastMarkIdx = [...bodyLines].reverse().findIndex((l) => MARK_RE.test(l.trim()));
  const lastMark = lastMarkIdx >= 0 ? bodyLines.length - 1 - lastMarkIdx : -1;
  const restBody = hasStructuredMarks && lastMark >= 0
    ? bodyLines.slice(lastMark + 1).join("\n").trim()
    : "";

  return (
    <div className="max-w-[680px] mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <Link href="/tipsters" className="text-[#1565C0] hover:underline font-bold">予想家</Link>
        {tipster && (
          <>
            <span className="mx-1 text-[#999]">&gt;</span>
            <Link href={`/tipsters/${encodeURIComponent(tipster.line_user_id)}`}
              className="text-[#1565C0] hover:underline font-bold">
              {tipster.display_name}
            </Link>
          </>
        )}
        <span className="mx-1 text-[#999]">&gt;</span>
        <span className="truncate">{article.title}</span>
      </div>

      {/* Race badge */}
      {article.race_id && (
        <Link href={`/race/${raceIdToPath(article.race_id ?? "")}`}
          className="inline-flex items-center gap-1.5 bg-[#163016] text-[#4ade80] text-[11px] font-bold px-3 py-1 rounded-full mb-3 hover:bg-[#1f4d1f] transition">
          ← レースページを見る
        </Link>
      )}

      {/* Tipster card */}
      <div className="flex items-center gap-3 mb-4 p-3 border border-[#e8d99a] rounded-xl bg-[#fffbeb]">
        <Link href={`/tipsters/${encodeURIComponent(article.tipster_id || "")}`} className="shrink-0">
          {tipster?.picture_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={tipster.picture_url} alt=""
              className="w-12 h-12 rounded-full object-cover ring-2 ring-[#d4a017]" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#d4a017] to-[#f0c040] flex items-center justify-center text-white font-black text-lg ring-2 ring-[#d4a017]">
              {(tipster?.display_name || article.author || "?")[0]}
            </div>
          )}
        </Link>
        <div className="flex-1 min-w-0">
          <Link href={`/tipsters/${encodeURIComponent(article.tipster_id || "")}`}
            className="text-sm font-black text-[#111] hover:text-[#d4a017] transition">
            {tipster?.display_name || article.author}
          </Link>
          {tipster?.catchphrase && (
            <p className="text-[11px] text-[#b8860b] font-bold mt-0.5 line-clamp-1">{tipster.catchphrase}</p>
          )}
        </div>
        <span className="text-[9px] font-bold text-[#d4a017] bg-white border border-[#e8d99a] px-2 py-0.5 rounded-full shrink-0">公認</span>
      </div>

      <div className="flex items-start justify-between gap-3 mb-2">
        <h1 className="text-xl font-black text-[#1a1a1a] leading-tight">{article.title}</h1>
        {isAdmin && (
          <div className="flex items-center gap-1.5 shrink-0">
            <Link
              href={`/predictions/${encodeURIComponent(slug)}/edit`}
              className="text-[10px] font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-2.5 py-1 rounded transition"
            >
              編集
            </Link>
            {onDeleteRequest && (
              <button
                type="button"
                onClick={onDeleteRequest}
                disabled={deleting}
                className="text-[10px] font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-2.5 py-1 rounded transition disabled:opacity-40"
              >
                {deleting ? "削除中..." : "削除"}
              </button>
            )}
          </div>
        )}
      </div>
      <p className="text-[11px] text-[#999] mb-4">{formatDate(article.created_at)}</p>

      {/* Preview / teaser */}
      {article.preview_body && (
        <div className="bg-[#f8f8f8] border border-[#e0e0e0] rounded-lg px-4 py-3 mb-4">
          <p className="text-[11px] font-bold text-[#888] mb-1">見解プレビュー</p>
          <p className="text-sm text-[#444] leading-relaxed">{article.preview_body}</p>
        </div>
      )}

      {/* Stats */}
      {(article.bet_method || (article.ticket_count && article.ticket_count > 0)) && (
        <div className="flex flex-wrap gap-3 mb-4">
          {article.bet_method && (
            <div className="border border-[#e0e0e0] rounded-lg px-3 py-2 text-center">
              <p className="text-[9px] text-[#999] font-bold mb-0.5">買い方</p>
              <p className="text-xs font-bold text-[#333]">{article.bet_method}</p>
            </div>
          )}
          {article.ticket_count != null && article.ticket_count > 0 && (
            <div className="border border-[#e0e0e0] rounded-lg px-3 py-2 text-center">
              <p className="text-[9px] text-[#999] font-bold mb-0.5">点数</p>
              <p className="text-xs font-bold text-[#333]">{article.ticket_count}点</p>
            </div>
          )}
        </div>
      )}

      {/* Body / locked */}
      {!canRead ? (
        <div className="border-2 border-dashed border-[#d4a017] rounded-xl p-6 text-center bg-[#fffbeb]">
          <p className="text-2xl mb-2">🔒</p>
          <p className="text-sm font-bold text-[#7c5c00] mb-1">プレミア予想</p>
          <p className="text-xs text-[#999]">この予想を見るにはポイントが必要です</p>
        </div>
      ) : (
        <>
          {/* Structured marks section */}
          {hasStructuredMarks && (
            <div className="border border-[#e0e0e0] rounded-xl overflow-hidden mb-4">
              <div className="bg-[#163016] px-4 py-2">
                <p className="text-sm font-black text-white">予想印</p>
              </div>
              <div className="divide-y divide-[#f0f0f0]">
                {marks.map((m, i) => {
                  const style = MARK_STYLE[m.mark] || { label: m.mark, color: "#333", bg: "#fff" };
                  const wakuClass = WAKU_BG[m.post || 0] || "bg-[#f0f0f0] text-[#333]";
                  return (
                    <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="w-7 text-xl font-black shrink-0" style={{ color: style.color }}>
                        {style.label}
                      </span>
                      {m.post ? (
                        <span className={`w-6 h-6 rounded text-[11px] font-bold flex items-center justify-center shrink-0 ${wakuClass}`}>
                          {m.post}
                        </span>
                      ) : null}
                      <span className="w-6 h-6 rounded-full bg-[#f0f0f0] flex items-center justify-center text-[11px] font-bold text-[#333] shrink-0">
                        {m.horseNumber}
                      </span>
                      <span className="flex-1 text-sm font-bold text-[#222]">{m.horseName}</span>
                      {m.popularity && (
                        <span className="text-[11px] text-[#999] shrink-0">({m.popularity}人気)</span>
                      )}
                    </div>
                  );
                })}
              </div>
              {/* Mark legend */}
              <div className="px-4 py-2 bg-[#f9f9f9] flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-[#888]">
                <span><span className="font-black text-[#c62828]">◎</span>本命</span>
                <span><span className="font-bold text-[#c62828]">○</span>対抗</span>
                <span><span className="font-bold text-[#1565c0]">▲</span>単穴</span>
                <span><span className="text-[#1565c0]">△</span>連下</span>
                <span><span className="text-[#f57c00]">☆</span>注目</span>
                <span><span className="font-bold text-[#888]">✖</span>消し</span>
              </div>
            </div>
          )}

          {/* Rest of body (buy tickets, analysis text) */}
          {restBody && (
            <div className="prose-nk">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{restBody}</ReactMarkdown>
            </div>
          )}

          {/* Fallback: plain body if no marks parsed */}
          {!hasStructuredMarks && (
            <div className="prose-nk">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{article.body}</ReactMarkdown>
            </div>
          )}
        </>
      )}

      <div className="mt-8 pt-5 border-t border-[#e5e5e5] flex items-center justify-between">
        <ShareButton
          title={article.title}
          url={`${SITE_URL}/articles/${encodeURIComponent(slug)}`}
        />
        <Link href="/tipsters" className="text-xs font-bold text-[#666] hover:text-[#1f7a1f] transition">
          ← 予想家一覧
        </Link>
      </div>
    </div>
  );
}
