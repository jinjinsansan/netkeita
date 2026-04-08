"use client";

import Link from "next/link";
import type { ArticleSummary, TipsterProfile } from "@/lib/api";

interface PredictionCardProps {
  prediction: ArticleSummary;
  tipster?: TipsterProfile | null;
  hasPremium?: boolean;
}

function parseRaceId(raceId?: string): string | null {
  if (!raceId) return null;
  // format: YYYYMMDD-venue-raceNum  e.g. "20260408-川崎-11"
  const parts = raceId.split("-");
  if (parts.length < 3) return null;
  const dateStr = parts[0];
  const venue = parts[1];
  const raceNum = parts[2];
  if (!dateStr || dateStr.length < 8) return null;
  const month = parseInt(dateStr.slice(4, 6), 10);
  const day = parseInt(dateStr.slice(6, 8), 10);
  return `${venue} ${raceNum}R (${month}/${day})`;
}

export default function PredictionCard({ prediction, tipster, hasPremium }: PredictionCardProps) {
  const isPremium = !!prediction.is_premium;
  const isFree = !isPremium;
  const isPurchased = isPremium && hasPremium;
  const displayCount = prediction.preview_body?.length ?? 0;
  const raceLabel = parseRaceId(prediction.race_id);

  return (
    <div className="border border-[#e0e0e0] rounded-xl bg-white overflow-hidden shadow-sm">
      {/* Catchphrase banner */}
      {tipster?.catchphrase && (
        <div className="bg-[#163016] px-3 py-1.5 text-[11px] font-bold text-[#4ade80] leading-tight">
          {tipster.catchphrase}
        </div>
      )}

      <div className="p-3">
        {/* Tipster row */}
        <div className="flex items-center gap-2.5 mb-2.5">
          <Link href={`/tipsters/${encodeURIComponent(prediction.tipster_id || "")}`} className="shrink-0">
            {tipster?.picture_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={tipster.picture_url} alt={tipster.display_name}
                className="w-11 h-11 rounded-full object-cover bg-[#eee] ring-2 ring-[#e0e0e0]" />
            ) : (
              <div className="w-11 h-11 rounded-full bg-gradient-to-br from-[#d4a017] to-[#f0c040] flex items-center justify-center text-white font-black text-base ring-2 ring-[#e0e0e0]">
                {(tipster?.display_name || prediction.author || "?")[0]}
              </div>
            )}
          </Link>
          <div className="flex-1 min-w-0">
            <Link href={`/tipsters/${encodeURIComponent(prediction.tipster_id || "")}`}
              className="text-sm font-black text-[#111] hover:text-[#d4a017] transition truncate block">
              {tipster?.display_name || prediction.author}
            </Link>
            {raceLabel && (
              <span className="inline-flex items-center gap-1 mt-0.5 text-[11px] font-bold text-[#b8860b]">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {raceLabel}
              </span>
            )}
          </div>
        </div>

        {/* Preview text */}
        {prediction.preview_body && (
          <p className="text-[13px] text-[#333] leading-relaxed mb-2 line-clamp-2">
            {prediction.preview_body}
          </p>
        )}

        {/* Stats row */}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-[#666] mb-3">
          {displayCount > 0 && (
            <span>見解: 約{displayCount}文字</span>
          )}
          {prediction.bet_method && (
            <span>買い方: {prediction.bet_method}</span>
          )}
          {prediction.ticket_count != null && prediction.ticket_count > 0 && (
            <span>点数: {prediction.ticket_count}点</span>
          )}
        </div>

        {/* CTA button */}
        <div className="flex justify-end">
          {isFree ? (
            <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-[#1f7a1f] hover:bg-[#16611a] px-4 py-1.5 rounded-lg transition">
              無料公開・予想を見る
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
          ) : isPurchased ? (
            <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-[#757575] hover:bg-[#616161] px-4 py-1.5 rounded-lg transition">
              購入済み・予想を見る
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
          ) : (
            <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-white bg-[#d4a017] hover:bg-[#b8860b] px-4 py-1.5 rounded-lg transition">
              プレミア予想を見る
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
