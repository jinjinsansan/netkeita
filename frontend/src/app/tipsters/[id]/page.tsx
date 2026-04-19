"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchTipster, fetchPremiumStatus } from "@/lib/api";
import type { TipsterProfile, ArticleSummary } from "@/lib/api";
import PredictionCard from "@/components/PredictionCard";
import { useAuth } from "@/lib/auth-context";

function todayJSTPrefix(): string {
  const now = new Date();
  // JST 変換: UTC+9
  const jst = new Date(now.getTime() + (9 * 60 + now.getTimezoneOffset()) * 60 * 1000);
  const y = jst.getFullYear();
  const m = String(jst.getMonth() + 1).padStart(2, "0");
  const d = String(jst.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
}

export default function TipsterPage() {
  const params = useParams();
  const id = decodeURIComponent(params.id as string);
  const { user } = useAuth();

  const [profile, setProfile] = useState<TipsterProfile | null>(null);
  const [predictions, setPredictions] = useState<ArticleSummary[]>([]);
  const [hasPremium, setHasPremium] = useState(false);
  const [loading, setLoading] = useState(true);
  const [predictionsLoading, setPredictionsLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [dayFilter, setDayFilter] = useState<"today" | "past">("today");

  // 初回ロード (プロファイル + 今日の予想)
  useEffect(() => {
    Promise.all([
      fetchTipster(id, "today"),
      user ? fetchPremiumStatus() : Promise.resolve(false),
    ]).then(([data, premium]) => {
      if (!data) {
        setNotFound(true);
      } else {
        setProfile(data.profile);
        setPredictions(data.predictions);
      }
      setHasPremium(!!premium || !!user?.is_admin);
      setLoading(false);
    });
  }, [id, user]);

  // タブ切替時の predictions 再取得 (profile は再フェッチ不要)
  const switchDay = async (next: "today" | "past") => {
    if (next === dayFilter) return;
    setDayFilter(next);
    setPredictionsLoading(true);
    const data = await fetchTipster(id, next);
    if (data) setPredictions(data.predictions);
    setPredictionsLoading(false);
  };

  // API 未対応時やネットワーク遅延時の保険として、race_id の日付プレフィックスで
  // クライアント側でも絞り込む。API が正しく絞っていればここは no-op と等価。
  const filteredPredictions = useMemo(() => {
    const today = todayJSTPrefix();
    return predictions.filter((p) => {
      const rid = (p.race_id || "").trim();
      const prefix = rid.split("-")[0] || "";
      if (!prefix) return false;
      return dayFilter === "today" ? prefix === today : prefix !== today;
    });
  }, [predictions, dayFilter]);

  if (loading) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10 animate-pulse space-y-4">
        <div className="h-40 bg-[#eee] rounded-xl" />
        <div className="space-y-2">
          <div className="h-5 bg-[#eee] rounded w-1/3" />
          <div className="h-3 bg-[#eee] rounded w-2/3" />
        </div>
      </div>
    );
  }

  if (notFound || !profile) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#999] mb-4">予想家が見つかりません</div>
        <Link href="/tipsters" className="text-xs font-bold text-[#1565C0] hover:underline">
          ← 予想家一覧へ
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[720px] mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <Link href="/tipsters" className="text-[#1565C0] hover:underline font-bold">予想家</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>{profile.display_name}</span>
      </div>

      {/* Profile card */}
      <div className="border border-[#e0e0e0] rounded-xl overflow-hidden shadow-sm mb-6">
        {/* Catchphrase banner */}
        {profile.catchphrase && (
          <div className="bg-[#163016] px-5 py-2.5 text-[13px] font-bold text-[#4ade80] leading-tight">
            {profile.catchphrase}
          </div>
        )}

        <div className="bg-white p-5">
          <div className="flex items-start gap-4">
            {/* Avatar with gold ring */}
            <div className="relative shrink-0">
              {profile.picture_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={profile.picture_url} alt={profile.display_name}
                  className="w-20 h-20 rounded-full object-cover ring-[3px] ring-[#d4a017]" />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#d4a017] to-[#f0c040] flex items-center justify-center text-3xl font-black text-white ring-[3px] ring-[#d4a017]">
                  {profile.display_name[0]}
                </div>
              )}
              {/* certified badge */}
              <span className="absolute -bottom-0.5 -right-0.5 w-6 h-6 bg-[#d4a017] rounded-full flex items-center justify-center shadow">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="white"><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></svg>
              </span>
            </div>

            {/* Name + badge + description */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <h1 className="text-xl font-black text-[#111]">{profile.display_name}</h1>
                <span className="text-[9px] font-bold text-[#d4a017] bg-[#fffbeb] border border-[#e8d99a] px-1.5 py-0.5 rounded-full shrink-0">公認</span>
              </div>
              {profile.description && (
                <p className="text-[13px] text-[#444] leading-relaxed">{profile.description}</p>
              )}
            </div>
          </div>

          {/* SNS links */}
          {profile.sns_links && Object.values(profile.sns_links).some(Boolean) && (
            <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-[#f0f0f0]">
              {profile.sns_links.x && (
                <a href={profile.sns_links.x} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] font-bold text-[#111] border border-[#d0d0d0] hover:border-black px-2.5 py-1 rounded-full transition">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.747l7.73-8.835L1.254 2.25H8.08l4.259 5.631L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z"/></svg>
                  X
                </a>
              )}
              {profile.sns_links.youtube && (
                <a href={profile.sns_links.youtube} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] font-bold text-[#555] hover:text-[#ff0000] border border-[#d0d0d0] hover:border-[#ff0000] px-2.5 py-1 rounded-full transition">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                  YouTube
                </a>
              )}
              {profile.sns_links.instagram && (
                <a href={profile.sns_links.instagram} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] font-bold text-[#555] hover:text-[#e1306c] border border-[#d0d0d0] hover:border-[#e1306c] px-2.5 py-1 rounded-full transition">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>
                  Instagram
                </a>
              )}
              {profile.sns_links.tiktok && (
                <a href={profile.sns_links.tiktok} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] font-bold text-[#555] border border-[#d0d0d0] hover:border-[#010101] px-2.5 py-1 rounded-full transition">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"/></svg>
                  TikTok
                </a>
              )}
              {profile.sns_links.note && (
                <a href={profile.sns_links.note} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] font-bold text-[#555] hover:text-[#41c9b4] border border-[#d0d0d0] hover:border-[#41c9b4] px-2.5 py-1 rounded-full transition">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M18.43 0H5.57A5.57 5.57 0 0 0 0 5.57v12.86A5.57 5.57 0 0 0 5.57 24h12.86A5.57 5.57 0 0 0 24 18.43V5.57A5.57 5.57 0 0 0 18.43 0zM7.37 6.2h3.73l2.44 6.04 2.44-6.04h3.65v11.6h-2.72v-7.4l-2.64 6.56h-1.42l-2.64-6.56v7.4H7.37V6.2z"/></svg>
                  note
                </a>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Predictions */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-black text-[#222]">
          予想一覧
          {filteredPredictions.length > 0 && (
            <span className="text-[11px] font-normal text-[#999] ml-2">{filteredPredictions.length}件</span>
          )}
        </h2>
      </div>

      {/* Day filter tabs: 今日 / 過去 */}
      <div
        role="tablist"
        aria-label="予想の期間"
        className="inline-flex items-center gap-1 p-1 mb-4 bg-[#f0f4f0] rounded-full border border-[#e0e6e0]"
      >
        {[
          { value: "today", label: "今日の予想" },
          { value: "past", label: "過去の予想" },
        ].map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={dayFilter === t.value}
            onClick={() => switchDay(t.value as "today" | "past")}
            className={`px-4 py-1.5 text-xs font-bold rounded-full transition
              ${dayFilter === t.value
                ? "bg-[#163016] text-white shadow-sm"
                : "text-[#4a5d4a] hover:bg-white/60"
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {predictionsLoading ? (
        <div className="border border-dashed border-[#e0e0e0] rounded-xl py-12 text-center animate-pulse">
          <p className="text-xs text-[#bbb]">読み込み中...</p>
        </div>
      ) : filteredPredictions.length === 0 ? (
        <div className="border border-dashed border-[#e0e0e0] rounded-xl py-12 text-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ccc" strokeWidth="1.5" className="mx-auto mb-3"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
          <p className="text-sm font-bold text-[#aaa] mb-1">
            {dayFilter === "today" ? "今日はまだ予想が投稿されていません" : "過去の予想はありません"}
          </p>
          <p className="text-xs text-[#bbb]">
            {dayFilter === "today" ? "AI予想家は毎朝6:00に予想を公開します" : ""}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredPredictions.map((p) => (
            <PredictionCard
              key={p.slug}
              prediction={p}
              tipster={profile}
              hasPremium={hasPremium}
            />
          ))}
        </div>
      )}
    </div>
  );
}
