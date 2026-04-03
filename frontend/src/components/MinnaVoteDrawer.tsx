"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchVoteResults, submitVote } from "@/lib/api";
import type { VoteResults } from "@/lib/api";
import type { HorseRank } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";

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

export default function MinnaVoteDrawer({
  raceId,
  horses,
  onClose,
}: {
  raceId: string;
  horses: HorseRank[];
  onClose: () => void;
}) {
  const { authenticated } = useAuth();
  const [data, setData] = useState<VoteResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [voted, setVoted] = useState(false);

  const loadResults = useCallback(() => {
    fetchVoteResults(raceId).then((d) => {
      setData(d);
      if (d?.my_vote) {
        setSelected(d.my_vote);
        setVoted(true);
      }
      setLoading(false);
    });
  }, [raceId]);

  useEffect(() => {
    setLoading(true);
    setVoted(false);
    setSelected(null);
    loadResults();
    requestAnimationFrame(() => setVisible(true));
  }, [raceId, loadResults]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 250);
  }, [onClose]);

  const handleVote = async () => {
    if (!selected || submitting) return;
    setSubmitting(true);
    const res = await submitVote(raceId, selected);
    if (res.success) {
      setVoted(true);
      loadResults();
    }
    setSubmitting(false);
  };

  const sortedHorses = [...horses].sort((a, b) => a.horse_number - b.horse_number);
  const maxRate = data?.results?.[0]?.rate || 1;

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
          width: "min(85vw, 420px)",
          transform: visible ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#163016] shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">🗳️</span>
            <h2 className="text-sm font-bold text-white">みんなの予想</h2>
            {data && (
              <span className="text-[10px] text-[#a3c9a3] ml-1">
                {data.total_votes}票
              </span>
            )}
          </div>
          <button
            onClick={handleClose}
            className="text-white text-xl leading-none px-1 hover:text-[#4ade80] transition shrink-0"
            aria-label="閉じる"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="py-10 text-center text-xs text-[#888] animate-pulse">
              読み込み中...
            </div>
          ) : voted || !authenticated ? (
            /* Results view */
            <ResultsView
              data={data}
              maxRate={maxRate}
              myVote={data?.my_vote ?? null}
              authenticated={authenticated}
            />
          ) : (
            /* Voting view */
            <div className="p-4">
              <p className="text-xs text-[#666] mb-3">
                本命だと思う馬を1頭選んでください
              </p>
              <div className="space-y-1.5">
                {sortedHorses.map((h) => (
                  <button
                    key={h.horse_number}
                    onClick={() => setSelected(h.horse_number)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg border transition text-left ${
                      selected === h.horse_number
                        ? "border-[#1f7a1f] bg-[#f0f7f0] ring-1 ring-[#1f7a1f]"
                        : "border-[#d0d0d0] bg-white hover:bg-[#fafafa]"
                    }`}
                  >
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold shrink-0 ${
                        WAKU_BG[h.post] || ""
                      }`}
                    >
                      {h.post}
                    </span>
                    <span className="text-sm font-bold text-[#333] shrink-0 w-5 text-center">
                      {h.horse_number}
                    </span>
                    <span className="text-sm font-medium text-[#222] truncate flex-1">
                      {h.horse_name}
                    </span>
                    <span className="text-[10px] text-[#999] shrink-0">
                      {h.jockey}
                    </span>
                    {selected === h.horse_number && (
                      <span className="text-[#1f7a1f] text-sm font-bold shrink-0">
                        ✓
                      </span>
                    )}
                  </button>
                ))}
              </div>

              <button
                onClick={handleVote}
                disabled={!selected || submitting}
                className={`w-full mt-4 py-3 rounded-xl font-bold text-sm transition ${
                  selected && !submitting
                    ? "bg-[#1f7a1f] text-white hover:bg-[#16611a] shadow-md"
                    : "bg-[#d0d0d0] text-[#999] cursor-not-allowed"
                }`}
              >
                {submitting ? "投票中..." : "この馬に投票する"}
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function ResultsView({
  data,
  maxRate,
  myVote,
  authenticated,
}: {
  data: VoteResults | null;
  maxRate: number;
  myVote: number | null;
  authenticated: boolean;
}) {
  if (!data || data.results.length === 0) {
    return (
      <div className="py-10 text-center">
        <div className="text-3xl mb-3">🗳️</div>
        <div className="text-sm font-bold text-[#999]">まだ投票がありません</div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {!authenticated && (
        <div className="bg-[#f8f8f8] border border-dashed border-[#d0d0d0] rounded-lg p-3 mb-3 text-center">
          <p className="text-[11px] text-[#999]">
            ログインすると投票できます
          </p>
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-[#444]">投票結果</span>
        <span className="text-[10px] text-[#999]">
          全{data.total_votes}票
        </span>
      </div>

      <div className="space-y-2">
        {data.results.map((r, i) => {
          const isMyVote = myVote === r.horse_number;
          const barWidth = maxRate > 0 ? (r.rate / maxRate) * 100 : 0;
          const isTop = i === 0;

          return (
            <div
              key={r.horse_number}
              className={`rounded-lg border px-3 py-2.5 ${
                isMyVote
                  ? "border-[#1f7a1f] bg-[#f0f7f0]"
                  : isTop
                  ? "border-[#e8c800] bg-[#fffde7]"
                  : "border-[#e8e8e8] bg-white"
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                {isTop && (
                  <span className="text-xs">👑</span>
                )}
                <span
                  className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold shrink-0 ${
                    WAKU_BG[r.post] || ""
                  }`}
                >
                  {r.post}
                </span>
                <span className="text-xs font-bold text-[#333] shrink-0">
                  {r.horse_number}
                </span>
                <span className="text-xs font-bold text-[#222] truncate flex-1">
                  {r.horse_name}
                </span>
                {isMyVote && (
                  <span className="text-[9px] font-bold text-[#1f7a1f] bg-[#e8f5e9] px-1.5 py-0.5 rounded shrink-0">
                    あなた
                  </span>
                )}
                <span className={`text-sm font-black shrink-0 ${isTop ? "text-[#d4a017]" : "text-[#333]"}`}>
                  {r.rate}%
                </span>
              </div>
              <div className="h-2 bg-[#eee] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${barWidth}%`,
                    backgroundColor: isTop
                      ? "#d4a017"
                      : isMyVote
                      ? "#1f7a1f"
                      : "#888",
                  }}
                />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-[#999]">{r.jockey}</span>
                <span className="text-[10px] text-[#bbb]">{r.votes}票</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
