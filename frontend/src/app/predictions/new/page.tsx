"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { fetchRaces, createArticle, fetchMyTipsterProfile, fetchTipsters } from "@/lib/api";
import type { RaceSummary } from "@/lib/types";
import type { TipsterProfile } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";

const BET_METHODS = ["単勝", "複勝", "馬連", "馬単", "ワイド", "三連複", "三連単", "その他"];

interface BetEntry {
  method: string;
  customMethod: string;
  count: number | "";
}

export default function NewPredictionPage() {
  return (
    <AuthGuard>
      <NewPredictionForm />
    </AuthGuard>
  );
}

function NewPredictionForm() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  const [myTipster, setMyTipster] = useState<TipsterProfile | null | undefined>(undefined);
  const [allTipsters, setAllTipsters] = useState<TipsterProfile[]>([]);
  const [selectedTipsterId, setSelectedTipsterId] = useState("");
  const [races, setRaces] = useState<RaceSummary[]>([]);
  const [raceId, setRaceId] = useState("");
  const [title, setTitle] = useState("");
  const [previewBody, setPreviewBody] = useState("");
  const [body, setBody] = useState("");
  const [betEntries, setBetEntries] = useState<BetEntry[]>([{ method: "", customMethod: "", count: "" }]);
  const [isPremium, setIsPremium] = useState(false);
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMyTipsterProfile().then((p) => {
      setMyTipster(p);
      if (p && !isAdmin) setSelectedTipsterId(p.line_user_id);
    });
    if (isAdmin) {
      fetchTipsters().then((list) => {
        setAllTipsters(list);
        if (list.length > 0) setSelectedTipsterId(list[0].line_user_id);
      });
    }
    const today = new Date();
    const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}`;
    fetchRaces(dateStr).then((data) => {
      const all: RaceSummary[] = [];
      for (const v of data.venues) all.push(...v.races);
      setRaces(all);
    });
  }, [isAdmin]);

  // 読み込み中
  if (myTipster === undefined && !isAdmin) {
    return <div className="max-w-[800px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">読み込み中...</div>;
  }
  // 一般ユーザーで未承認
  if (!isAdmin && (!myTipster || myTipster.status !== "approved")) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#c62828] mb-4">承認済みの予想家のみ投稿できます</div>
        <Link href="/tipsters/apply" className="text-xs font-bold text-[#1f7a1f] hover:underline">
          予想家に申請する
        </Link>
      </div>
    );
  }

  const addBetEntry = () =>
    setBetEntries((prev) => [...prev, { method: "", customMethod: "", count: "" }]);

  const removeBetEntry = (idx: number) =>
    setBetEntries((prev) => prev.filter((_, i) => i !== idx));

  const updateBetEntry = (idx: number, patch: Partial<BetEntry>) =>
    setBetEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, ...patch } : e)));

  const buildBetMethod = () =>
    betEntries
      .map((e) => {
        const m = e.method === "その他" ? e.customMethod.trim() : e.method;
        if (!m) return "";
        return e.count ? `${m} ${e.count}点` : m;
      })
      .filter(Boolean)
      .join(" / ");

  const buildTicketCount = () =>
    betEntries.reduce((s, e) => s + (Number(e.count) || 0), 0);

  const handleSubmit = async (status: "published" | "draft") => {
    if (!raceId) { setError("対象レースを選択してください"); return; }
    if (!title.trim()) { setError("タイトルを入力してください"); return; }
    if (!previewBody.trim()) { setError("見解プレビューを入力してください"); return; }
    if (!selectedTipsterId) { setError("投稿する予想家を選択してください"); return; }
    setError(null);
    setSubmitting(true);
    const res = await createArticle({
      title: title.trim(),
      body,
      preview_body: previewBody.trim(),
      bet_method: buildBetMethod(),
      ticket_count: buildTicketCount(),
      is_premium: isPremium,
      race_id: raceId,
      content_type: "prediction",
      tipster_id: selectedTipsterId,
      status,
    });
    if (res.success) {
      router.push(`/articles/${encodeURIComponent(res.article.slug)}`);
    } else {
      setError(res.error || "投稿に失敗しました");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-[800px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>予想を投稿</span>
      </div>

      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-black text-[#222]">予想を投稿</h1>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleSubmit("draft")}
            className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition disabled:opacity-40"
          >
            下書き保存
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleSubmit("published")}
            className="text-xs font-bold bg-[#1f7a1f] hover:bg-[#16611a] text-white px-4 py-2 rounded-lg transition disabled:opacity-40"
          >
            {submitting ? "送信中..." : "公開する"}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Tipster selector (admin only) */}
        {isAdmin && (
          <div className="rounded-lg border border-[#1565C0]/30 bg-[#f0f4ff] p-3">
            <label className="block text-[11px] font-bold text-[#1565C0] mb-1">
              投稿する予想家 <span className="text-[#c62828]">*</span>
            </label>
            {allTipsters.length === 0 ? (
              <p className="text-xs text-[#888]">承認済みの予想家がいません</p>
            ) : (
              <select
                value={selectedTipsterId}
                onChange={(e) => setSelectedTipsterId(e.target.value)}
                className="w-full border border-[#b0c4e8] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1565C0]"
              >
                {allTipsters.map((t) => (
                  <option key={t.line_user_id} value={t.line_user_id}>
                    {t.display_name}
                    {(t as TipsterProfile & { is_managed?: boolean }).is_managed ? " [管理者作成]" : ""}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Race selector */}
        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            対象レース <span className="text-[#c62828]">*</span>
          </label>
          <select
            value={raceId}
            onChange={(e) => setRaceId(e.target.value)}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1f7a1f]"
          >
            <option value="">レースを選択</option>
            {races.map((r) => (
              <option key={r.race_id} value={r.race_id}>
                {r.venue} {r.race_number}R {r.race_name} ({r.distance}, {r.headcount}頭)
              </option>
            ))}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            タイトル <span className="text-[#c62828]">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value.slice(0, 200))}
            placeholder="例: 川崎記念 予想"
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
        </div>

        {/* Bet entries (multiple) */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">買い目 (任意)</label>
            <button
              type="button"
              onClick={addBetEntry}
              className="text-[10px] font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-2 py-0.5 rounded transition"
            >
              ＋ 追加
            </button>
          </div>
          <div className="space-y-2">
            {betEntries.map((entry, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <div>
                    <select
                      value={entry.method}
                      onChange={(e) => updateBetEntry(idx, { method: e.target.value })}
                      className="w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:border-[#1f7a1f]"
                    >
                      <option value="">買い方を選択</option>
                      {BET_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                    {entry.method === "その他" && (
                      <input
                        type="text"
                        value={entry.customMethod}
                        onChange={(e) => updateBetEntry(idx, { customMethod: e.target.value.slice(0, 100) })}
                        placeholder="買い方を入力"
                        className="mt-1 w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm focus:outline-none focus:border-[#1f7a1f]"
                      />
                    )}
                  </div>
                  <input
                    type="number"
                    min={1}
                    max={999}
                    value={entry.count}
                    onChange={(e) => updateBetEntry(idx, { count: e.target.value === "" ? "" : Number(e.target.value) })}
                    placeholder="点数 (任意)"
                    className="w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm focus:outline-none focus:border-[#1f7a1f]"
                  />
                </div>
                {betEntries.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeBetEntry(idx)}
                    className="mt-1 text-[#c62828] hover:text-[#a32020] text-lg font-bold leading-none"
                    aria-label="削除"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Preview body */}
        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            見解プレビュー <span className="text-[#c62828]">*</span>
            <span className="text-[#999] font-normal ml-1">— 有料・無料問わず全員に見える文章</span>
          </label>
          <textarea
            value={previewBody}
            onChange={(e) => setPreviewBody(e.target.value.slice(0, 300))}
            placeholder="今回の注目ポイントを一言で伝えてください"
            rows={3}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
          <p className="text-[10px] text-[#999] mt-0.5">{previewBody.length} / 300</p>
        </div>

        {/* Premium toggle */}
        <label className="flex items-center gap-2 text-sm font-bold text-[#444] cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isPremium}
            onChange={(e) => setIsPremium(e.target.checked)}
            className="w-4 h-4"
          />
          有料予想にする
          <span className="text-[11px] font-normal text-[#888]">
            (管理者がアクセス権を付与したユーザーのみ本文を閲覧できます)
          </span>
        </label>

        {/* Body */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">
              本文（買い目・分析）
              {isPremium && <span className="text-[#d4a017] font-normal ml-1">— 有料ユーザーのみ閲覧</span>}
            </label>
            <div className="flex gap-1">
              {(["edit", "preview"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`text-[10px] font-bold px-2 py-1 rounded transition ${mode === m ? "bg-[#1f7a1f] text-white" : "bg-[#f0f0f0] text-[#666]"}`}
                >
                  {m === "edit" ? "編集" : "プレビュー"}
                </button>
              ))}
            </div>
          </div>
          {mode === "edit" ? (
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder={`◎ 馬名\n○ 馬名\n▲ 馬名\n\n買い目:\n馬連 X-Y 1点\n...`}
              rows={12}
              className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f] font-mono"
            />
          ) : (
            <div className="border border-[#d0d0d0] rounded p-4 bg-white min-h-[200px] prose-nk">
              {body.trim() ? (
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{body}</ReactMarkdown>
              ) : (
                <p className="text-xs text-[#bbb]">本文が入力されるとここにプレビューが表示されます</p>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
