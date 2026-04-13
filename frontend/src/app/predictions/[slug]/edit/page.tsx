"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { fetchArticle, updateArticle, fetchRaces } from "@/lib/api";
import type { Article } from "@/lib/api";
import type { RaceSummary } from "@/lib/types";
import AuthGuard from "@/components/AuthGuard";

const BET_METHODS = ["単勝", "複勝", "馬連", "馬単", "ワイド", "三連複", "三連単", "その他"];

interface BetEntry {
  method: string;
  customMethod: string;
  count: number | "";
}

export default function EditPredictionPage() {
  return (
    <AuthGuard>
      <EditForm />
    </AuthGuard>
  );
}

function EditForm() {
  const params = useParams();
  const router = useRouter();
  const slug = decodeURIComponent(params.slug as string);

  const [article, setArticle] = useState<Article | null>(null);
  const [races, setRaces] = useState<RaceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [title, setTitle] = useState("");
  const [previewBody, setPreviewBody] = useState("");
  const [body, setBody] = useState("");
  const [betEntries, setBetEntries] = useState<BetEntry[]>([{ method: "", customMethod: "", count: "" }]);
  const [isPremium, setIsPremium] = useState(false);
  const [raceId, setRaceId] = useState("");
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchArticle(slug),
      (() => {
        const today = new Date();
        const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}`;
        return fetchRaces(dateStr);
      })(),
    ]).then(([art, racesData]) => {
      if (!art) { setNotFound(true); setLoading(false); return; }
      setArticle(art);
      setTitle(art.title || "");
      setPreviewBody(art.preview_body || "");
      setBody(art.body || "");
      setIsPremium(!!art.is_premium);
      setRaceId(art.race_id || "");
      // Parse saved bet_method back into entries.
      // Format stored by new editor: "馬連 3点 / 三連単 1点"
      // Fallback: treat the whole string as a single entry.
      const bm = art.bet_method || "";
      if (bm) {
        const parts = bm.split(" / ").map((s) => s.trim()).filter(Boolean);
        const parsed: BetEntry[] = parts.map((part) => {
          const m = part.match(/^(.+?)\s+(\d+)点$/) || part.match(/^(.+)$/);
          if (!m) return { method: "", customMethod: part, count: "" };
          const methodStr = m[1].trim();
          const count = m[2] ? Number(m[2]) : "";
          if (BET_METHODS.includes(methodStr)) return { method: methodStr, customMethod: "", count };
          return { method: "その他", customMethod: methodStr, count };
        });
        setBetEntries(parsed.length ? parsed : [{ method: "", customMethod: "", count: "" }]);
      }
      const all: RaceSummary[] = [];
      for (const v of racesData.venues) all.push(...v.races);
      setRaces(all);
      setLoading(false);
    });
  }, [slug]);

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
    if (!title.trim()) { setError("タイトルを入力してください"); return; }
    if (!previewBody.trim()) { setError("見解プレビューを入力してください"); return; }
    setError(null);
    setSubmitting(true);
    const res = await updateArticle(slug, {
      title: title.trim(),
      body,
      preview_body: previewBody.trim(),
      bet_method: buildBetMethod(),
      ticket_count: buildTicketCount(),
      is_premium: isPremium,
      race_id: raceId,
      status,
      expected_updated_at: article?.updated_at,
    });
    if (res.success) {
      router.push("/tipsters/dashboard");
    } else {
      setError(res.error || "更新に失敗しました");
      setSubmitting(false);
    }
  };

  if (loading) return <div className="max-w-[800px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">読み込み中...</div>;
  if (notFound) return (
    <div className="max-w-[800px] mx-auto px-4 py-10 text-center">
      <p className="text-sm text-[#999] mb-4">予想が見つかりません</p>
      <Link href="/tipsters/dashboard" className="text-xs font-bold text-[#1f7a1f] hover:underline">← ダッシュボードへ</Link>
    </div>
  );

  return (
    <div className="max-w-[800px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/tipsters/dashboard" className="text-[#1565C0] hover:underline font-bold">ダッシュボード</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>予想を編集</span>
      </div>

      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-black text-[#222]">予想を編集</h1>
        <div className="flex gap-2">
          <button type="button" disabled={submitting} onClick={() => handleSubmit("draft")}
            className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition disabled:opacity-40">
            下書き保存
          </button>
          <button type="button" disabled={submitting} onClick={() => handleSubmit("published")}
            className="text-xs font-bold bg-[#1f7a1f] hover:bg-[#16611a] text-white px-4 py-2 rounded-lg transition disabled:opacity-40">
            {submitting ? "送信中..." : "更新して公開"}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">対象レース</label>
          <select value={raceId} onChange={(e) => setRaceId(e.target.value)}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1f7a1f]">
            <option value="">レースを選択しない</option>
            {races.map((r) => (
              <option key={r.race_id} value={r.race_id}>
                {r.venue} {r.race_number}R {r.race_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">タイトル <span className="text-[#c62828]">*</span></label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value.slice(0, 200))}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]" />
        </div>

        {/* Bet entries (multiple) */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">買い目 (任意)</label>
            <button type="button" onClick={addBetEntry}
              className="text-[10px] font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-2 py-0.5 rounded transition">
              ＋ 追加
            </button>
          </div>
          <div className="space-y-2">
            {betEntries.map((entry, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <div className="flex-1 grid grid-cols-2 gap-2">
                  <div>
                    <select value={entry.method} onChange={(e) => updateBetEntry(idx, { method: e.target.value })}
                      className="w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:border-[#1f7a1f]">
                      <option value="">買い方を選択</option>
                      {BET_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                    {entry.method === "その他" && (
                      <input type="text" value={entry.customMethod}
                        onChange={(e) => updateBetEntry(idx, { customMethod: e.target.value.slice(0, 100) })}
                        placeholder="買い方を入力"
                        className="mt-1 w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm focus:outline-none focus:border-[#1f7a1f]" />
                    )}
                  </div>
                  <input type="number" min={1} max={999} value={entry.count}
                    onChange={(e) => updateBetEntry(idx, { count: e.target.value === "" ? "" : Number(e.target.value) })}
                    placeholder="点数 (任意)"
                    className="w-full border border-[#d0d0d0] rounded px-2 py-1.5 text-sm focus:outline-none focus:border-[#1f7a1f]" />
                </div>
                {betEntries.length > 1 && (
                  <button type="button" onClick={() => removeBetEntry(idx)}
                    className="mt-1 text-[#c62828] hover:text-[#a32020] text-lg font-bold leading-none" aria-label="削除">
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            見解プレビュー <span className="text-[#c62828]">*</span>
            <span className="text-[#999] font-normal ml-1">— 全員に見える文章</span>
          </label>
          <textarea value={previewBody} onChange={(e) => setPreviewBody(e.target.value.slice(0, 300))}
            rows={3} className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]" />
          <p className="text-[10px] text-[#999] mt-0.5">{previewBody.length} / 300</p>
        </div>

        <label className="flex items-center gap-2 text-sm font-bold text-[#444] cursor-pointer select-none">
          <input type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)} className="w-4 h-4" />
          有料予想にする
        </label>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">本文（買い目・分析）</label>
            <div className="flex gap-1">
              {(["edit", "preview"] as const).map((m) => (
                <button key={m} type="button" onClick={() => setMode(m)}
                  className={`text-[10px] font-bold px-2 py-1 rounded transition ${mode === m ? "bg-[#1f7a1f] text-white" : "bg-[#f0f0f0] text-[#666]"}`}>
                  {m === "edit" ? "編集" : "プレビュー"}
                </button>
              ))}
            </div>
          </div>
          {mode === "edit" ? (
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12}
              className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f] font-mono" />
          ) : (
            <div className="border border-[#d0d0d0] rounded p-4 bg-white min-h-[200px] prose-nk">
              {body.trim() ? <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{body}</ReactMarkdown>
                : <p className="text-xs text-[#bbb]">プレビューが表示されます</p>}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]">{error}</div>
        )}
      </div>
    </div>
  );
}
