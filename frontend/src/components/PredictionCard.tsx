"use client";

import Link from "next/link";
import type { ArticleSummary, TipsterProfile } from "@/lib/api";

interface PredictionCardProps {
  prediction: ArticleSummary;
  tipster?: TipsterProfile | null;
  hasPremium?: boolean;
}

export default function PredictionCard({ prediction, tipster, hasPremium }: PredictionCardProps) {
  const isPremium = !!prediction.is_premium;
  const bodyAvailable = !isPremium || hasPremium;
  const charCount = prediction.preview_body
    ? `約${prediction.preview_body.length}文字`
    : null;

  return (
    <div className="border border-[#d0d0d0] rounded-lg bg-white overflow-hidden">
      {/* Badge row */}
      {tipster?.catchphrase && (
        <div className="bg-[#fff8e1] border-b border-[#ffe082] px-3 py-1.5 text-[11px] font-bold text-[#7c5c00]">
          {tipster.catchphrase}
        </div>
      )}

      <div className="p-3">
        {/* Tipster header */}
        <div className="flex items-center gap-2.5 mb-2">
          {tipster?.picture_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={tipster.picture_url}
              alt={tipster.display_name}
              className="w-9 h-9 rounded-full object-cover bg-[#eee] shrink-0"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-[#e0e0e0] flex items-center justify-center shrink-0 text-[#888] text-xs font-bold">
              {(tipster?.display_name || prediction.author || "?")[0]}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <Link
              href={`/tipsters/${encodeURIComponent(prediction.tipster_id || "")}`}
              className="text-sm font-bold text-[#1565C0] hover:underline truncate block"
            >
              {tipster?.display_name || prediction.author}
            </Link>
          </div>
          {isPremium ? (
            <span className="shrink-0 text-[10px] font-bold text-white bg-[#d4a017] px-2 py-0.5 rounded">
              有料
            </span>
          ) : (
            <span className="shrink-0 text-[10px] font-bold text-[#1f7a1f] bg-[#e8f5e9] px-2 py-0.5 rounded">
              無料
            </span>
          )}
        </div>

        {/* Preview text */}
        {prediction.preview_body && (
          <p className="text-[13px] text-[#444] leading-relaxed mb-2 line-clamp-2">
            {prediction.preview_body}
          </p>
        )}

        {/* Stats row */}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-[#666] mb-3">
          {charCount && (
            <span>見解: {charCount}</span>
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
          {bodyAvailable ? (
            <Link
              href={`/articles/${encodeURIComponent(prediction.slug)}`}
              className="text-xs font-bold text-white bg-[#1f7a1f] hover:bg-[#16611a] px-4 py-2 rounded-lg transition"
            >
              {isPremium ? "購入済み・予想を見る" : "無料で見る"}
            </Link>
          ) : (
            <Link
              href={`/articles/${encodeURIComponent(prediction.slug)}`}
              className="text-xs font-bold text-white bg-[#d4a017] hover:bg-[#b8860b] px-4 py-2 rounded-lg transition"
            >
              有料予想を見る
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
