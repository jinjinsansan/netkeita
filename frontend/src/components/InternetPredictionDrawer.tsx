"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchInternetPredictions } from "@/lib/api";
import type { InternetPrediction } from "@/lib/api";

export default function InternetPredictionDrawer({
  raceName,
  onClose,
}: {
  raceName: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<InternetPrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchInternetPredictions(raceName).then((d) => {
      setData(d);
      setLoading(false);
    });
    requestAnimationFrame(() => setVisible(true));
  }, [raceName]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 250);
  }, [onClose]);

  return (
    <>
      <div
        className="fixed inset-0 z-[60] transition-opacity duration-250"
        style={{ background: visible ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0)" }}
        onClick={handleClose}
      />
      <div
        className="fixed top-0 right-0 z-[61] h-full flex flex-col bg-white shadow-lg transition-transform duration-250"
        style={{
          width: "min(90vw, 440px)",
          transform: visible ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#163016] shrink-0">
          <h2 className="text-sm font-bold text-white truncate">ネットの予想</h2>
          <button
            onClick={handleClose}
            className="text-white text-xl leading-none px-1 hover:text-[#4ade80] transition shrink-0 ml-2"
            aria-label="閉じる"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="py-10 text-center text-xs text-[#888]">読み込み中...</div>
          ) : !data ? (
            <div className="py-10 text-center text-xs text-[#888]">
              このレースのネット予想データはありません
            </div>
          ) : (
            <div className="space-y-6">
              {/* YouTube */}
              {data.youtube?.horses && data.youtube.horses.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1 h-5 bg-[#E53935] rounded-full" />
                    <h3 className="text-sm font-bold text-[#222]">
                      YouTube予想
                    </h3>
                    <span className="text-[11px] text-[#888]">
                      ({data.youtube.source_count}件集計)
                    </span>
                  </div>
                  <div className="space-y-1">
                    {data.youtube.horses.map((h) => (
                      <PredictionRow key={h.rank} horse={h} color="#E53935" />
                    ))}
                  </div>
                </div>
              )}

              {/* Keiba sites */}
              {data.keiba_site?.horses && data.keiba_site.horses.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1 h-5 bg-[#1565C0] rounded-full" />
                    <h3 className="text-sm font-bold text-[#222]">
                      大手競馬サイト
                    </h3>
                    <span className="text-[11px] text-[#888]">
                      ({data.keiba_site.source_count}件集計)
                    </span>
                  </div>
                  <div className="space-y-1">
                    {data.keiba_site.horses.map((h) => (
                      <PredictionRow key={h.rank} horse={h} color="#1565C0" />
                    ))}
                  </div>
                </div>
              )}

              {/* Highlights */}
              {data.highlights && data.highlights.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-1 h-5 bg-[#1f7a1f] rounded-full" />
                    <h3 className="text-sm font-bold text-[#222]">注目ポイント</h3>
                  </div>
                  <div className="bg-[#f8faf8] border border-[#d0d0d0] rounded-lg p-3 space-y-1.5">
                    {data.highlights.map((hl, i) => (
                      <p key={i} className="text-[13px] text-[#444] leading-relaxed">
                        ・{hl}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function PredictionRow({
  horse,
  color,
}: {
  horse: { rank: number; mark: string; name: string; support_rate: number };
  color: string;
}) {
  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-[#eee] last:border-0">
      <span className="text-base font-black w-6 text-center shrink-0" style={{ color }}>
        {horse.mark}
      </span>
      <span className="font-bold text-sm flex-1 text-[#222] truncate">{horse.name}</span>
      <span className="text-xs font-bold text-[#555] shrink-0 w-9 text-right">
        {horse.support_rate}%
      </span>
      <div className="w-16 h-2.5 bg-[#eee] rounded-full overflow-hidden shrink-0">
        <div
          className="h-full rounded-full"
          style={{ width: `${horse.support_rate}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}
