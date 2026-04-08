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
  const isFree = !isPremium;
  const isPurchased = isPremium && hasPremium;
  const displayCount = prediction.preview_body?.length ?? 0;

  return (
    <div className="border border-[#e0e0e0] rounded-xl bg-white overflow-hidden shadow-sm">
      {/* Badge */}
      {tipster?.catchphrase && (
        <div className="bg-[#e65100] px-3 py-1.5 text-[11px] font-bold text-white leading-tight">
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
        {isFree ? (
          <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
            className="block w-full text-center text-sm font-bold text-white bg-[#e53935] hover:bg-[#c62828] py-2.5 rounded-lg transition">
            無料公開<br />
            <span className="text-[11px] font-normal">予想を見る</span>
          </Link>
        ) : isPurchased ? (
          <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
            className="block w-full text-center text-sm font-bold text-white bg-[#757575] hover:bg-[#616161] py-2.5 rounded-lg transition">
            購入済み<br />
            <span className="text-[11px] font-normal">予想を見る</span>
          </Link>
        ) : (
          <Link href={`/articles/${encodeURIComponent(prediction.slug)}`}
            className="block w-full text-center text-sm font-bold text-white bg-[#d4a017] hover:bg-[#b8860b] py-2.5 rounded-lg transition">
            プレミア予想を見る<br />
            <span className="text-[11px] font-normal">ポイントで購入</span>
          </Link>
        )}
      </div>
    </div>
  );
}
