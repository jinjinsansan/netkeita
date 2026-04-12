"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchMyVoteHistory, fetchKReward, fetchUserProfile, updateUserProfile, uploadUserAvatar } from "@/lib/api";
import type { VoteHistory, VoteResultStatus, KRewardData, UserProfile } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { raceIdToPath } from "@/lib/venue-codes";

const AVATAR_EMOJI_MAP: Record<string, string> = {
  horse1: "🐴", horse2: "🏇", jockey1: "🥇", jockey2: "🎯",
  crown: "👑", fire: "🔥", diamond: "💎", clover: "🍀",
  thunder: "⚡", star: "🌟", slot: "🎰", eagle: "🦅",
};

export default function MyPage() {
  return (
    <AuthGuard>
      <MyPageContent />
    </AuthGuard>
  );
}

const RESULT_LABEL: Record<VoteResultStatus, { text: string; color: string; bg: string }> = {
  hit: { text: "的中", color: "#E53935", bg: "#fce4ec" },
  hit_no_payout: { text: "的中", color: "#E53935", bg: "#fce4ec" },
  miss: { text: "不的中", color: "#9E9E9E", bg: "#f5f5f5" },
  pending: { text: "結果待ち", color: "#F57C00", bg: "#fff3e0" },
  cancelled: { text: "中止", color: "#607D8B", bg: "#eceff1" },
};

// Auto-refresh interval: 60 seconds. Keeps pending races up-to-date after
// the cron (`scripts/update_race_results.py`) populates their results.
const REFRESH_INTERVAL_MS = 60_000;

function MyPageContent() {
  const { user } = useAuth();
  const [data, setData] = useState<VoteHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [kreward, setKreward] = useState<KRewardData | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [nickname, setNickname] = useState("");
  const [avatarKey, setAvatarKey] = useState("horse1");
  const [customAvatarUrl, setCustomAvatarUrl] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const [d, kr, prof] = await Promise.all([fetchMyVoteHistory(), fetchKReward(), fetchUserProfile()]);
    setData(d);
    setKreward(kr);
    if (prof) {
      setProfile(prof);
      setNickname(prof.nickname || "");
      setAvatarKey(prof.avatar_key || "horse1");
      setCustomAvatarUrl(prof.custom_avatar_url || null);
    }
    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  const handleProfileSave = async () => {
    setProfileSaving(true);
    setProfileMsg(null);
    const res = await updateUserProfile(nickname || undefined, customAvatarUrl ? undefined : avatarKey || undefined);
    setProfileMsg(res.success ? { ok: true, text: "保存しました！" } : { ok: false, text: res.error || "失敗しました" });
    setProfileSaving(false);
    setTimeout(() => setProfileMsg(null), 3000);
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarUploading(true);
    setProfileMsg(null);
    const res = await uploadUserAvatar(file);
    if (res.success && res.url) {
      setCustomAvatarUrl(res.url);
      setProfileMsg({ ok: true, text: "画像をアップロードしました！" });
      setTimeout(() => setProfileMsg(null), 3000);
    } else {
      setProfileMsg({ ok: false, text: res.error || "アップロードに失敗しました" });
    }
    setAvatarUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleClearCustomAvatar = async () => {
    setCustomAvatarUrl(null);
    const res = await updateUserProfile(undefined, avatarKey);
    if (!res.success) setProfileMsg({ ok: false, text: res.error || "リセットに失敗しました" });
    else setProfileMsg({ ok: true, text: "絵文字アバターに戻しました" });
    setTimeout(() => setProfileMsg(null), 3000);
  };



  useEffect(() => {
    load();
  }, [load]);

  // Periodic refresh so pending rows become finalised without a manual reload.
  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        load();
      }
    }, REFRESH_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        load();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  const formatTime = (d: Date) =>
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

  return (
    <div className="max-w-[960px] mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>マイページ</span>
      </div>

      {/* User header */}
      <div className="bg-[#163016] rounded-lg px-5 py-4 mb-5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full overflow-hidden bg-[#4ade80] flex items-center justify-center shrink-0">
          {customAvatarUrl ? (
            <img src={customAvatarUrl} alt="アバター" className="w-full h-full object-cover" />
          ) : (
            <span className="text-xl">{AVATAR_EMOJI_MAP[avatarKey] || "🐴"}</span>
          )}
        </div>
        <div>
          <div className="text-white font-bold text-sm">{nickname || user?.display_name || "ユーザー"}</div>
          <div className="text-[#a3c9a3] text-[11px]">マイページ</div>
        </div>
      </div>

      {/* プロフィール設定 */}
      <div className="border border-[#c8e6c9] rounded-xl bg-[#f1f8f1] p-4 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-base">👤</span>
          <span className="text-sm font-black text-[#163016]">チャット プロフィール設定</span>
        </div>

        {/* Current avatar preview */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-16 h-16 rounded-full bg-[#e8f5e9] border-2 border-[#4ade80] flex items-center justify-center overflow-hidden shrink-0">
            {customAvatarUrl ? (
              <img src={customAvatarUrl} alt="アバター" className="w-full h-full object-cover" />
            ) : (
              <span className="text-3xl">{AVATAR_EMOJI_MAP[avatarKey] || "🐴"}</span>
            )}
          </div>
          <div>
            <div className="text-xs font-bold text-[#333]">現在のアバター</div>
            <div className="text-[11px] text-[#888] mt-0.5">
              {customAvatarUrl ? "カスタム画像" : `絵文字: ${AVATAR_EMOJI_MAP[avatarKey]}`}
            </div>
            {customAvatarUrl && (
              <button
                onClick={handleClearCustomAvatar}
                className="text-[11px] text-red-500 hover:text-red-700 underline mt-1"
              >
                絵文字に戻す
              </button>
            )}
          </div>
        </div>

        {/* Custom image upload */}
        <div className="mb-4 p-3 bg-white border border-[#ddd] rounded-xl">
          <div className="text-[11px] text-[#555] font-bold mb-2">📷 カスタム画像をアップロード</div>
          <div className="text-[10px] text-[#888] mb-2">
            JPEG / PNG / WebP / GIF・最大5MB・デバイスから選択できます
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleAvatarUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={avatarUploading}
            className="flex items-center gap-2 px-4 py-2 bg-[#163016] text-white text-xs font-bold rounded-lg disabled:opacity-40 hover:bg-[#1f4a1f] transition-colors"
          >
            {avatarUploading ? (
              <>
                <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                アップロード中...
              </>
            ) : (
              <>📂 画像を選択してアップロード</>
            )}
          </button>
        </div>

        {/* Emoji avatar selector */}
        <div className="mb-4">
          <div className="text-[11px] text-[#555] font-bold mb-1.5">
            または絵文字アバターを選ぶ
            {customAvatarUrl && <span className="ml-1 text-[#999] font-normal">（選ぶとカスタム画像が解除されます）</span>}
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(AVATAR_EMOJI_MAP).map(([key, emoji]) => (
              <button
                key={key}
                onClick={() => { setAvatarKey(key); setCustomAvatarUrl(null); }}
                title={key}
                className={`w-10 h-10 rounded-full flex items-center justify-center text-xl transition-all ${
                  !customAvatarUrl && avatarKey === key
                    ? "bg-[#163016] ring-2 ring-[#4ade80] scale-110"
                    : "bg-white border border-[#ddd] hover:border-[#163016]"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>

        {/* Nickname */}
        <div className="mb-4">
          <div className="text-[11px] text-[#555] font-bold mb-1.5">ニックネーム（最大20文字）</div>
          <input
            type="text"
            value={nickname}
            maxLength={20}
            onChange={(e) => setNickname(e.target.value)}
            placeholder={profile?.display_name || "ニックネームを入力"}
            className="w-full text-base border border-[#ccc] rounded-lg px-3 py-2 focus:outline-none focus:border-[#163016] bg-white"
          />
          <div className="text-[10px] text-[#888] mt-1">
            ※チャットに表示される名前です。未設定の場合はLINE表示名を使用します。
          </div>
        </div>

        {/* Save button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleProfileSave}
            disabled={profileSaving || avatarUploading}
            className="px-4 py-2 bg-[#163016] text-white text-xs font-bold rounded-lg disabled:opacity-40 hover:bg-[#1f4a1f] transition-colors"
          >
            {profileSaving ? "保存中..." : "ニックネームを保存"}
          </button>
          {profileMsg && (
            <span className={`text-xs font-bold ${profileMsg.ok ? "text-[#163016]" : "text-red-600"}`}>
              {profileMsg.text}
            </span>
          )}
        </div>
      </div>

      {/* Kリワードセクション */}
      <div className="border border-[#e8d99a] rounded-xl bg-[#fffdf5] p-4 mb-5">
        {/* ヘッダー */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🏆</span>
            <span className="text-sm font-black text-[#7c5c00]">Kリワード</span>
            <span className="text-[10px] text-[#999] font-medium">的中ポイント</span>
          </div>
          <div className="text-right">
            {loading ? (
              <span className="text-2xl font-black text-[#e8d99a]">--</span>
            ) : (
              <span className="text-2xl font-black text-[#d4a017]">{kreward?.balance ?? 0}</span>
            )}
            <span className="text-xs text-[#b8860b] ml-1">pt</span>
          </div>
        </div>

        {/* ポイント倍率説明 */}
        <p className="text-[11px] text-[#888] mb-2">投票した馬が1着 → 単勝オッズに応じてpt付与</p>
        <div className="flex flex-wrap gap-1.5 mb-3">
          {[
            { label: "単勝〜10倍", pt: "+10pt", color: "#4ade80", bg: "#163016" },
            { label: "単勝〜30倍", pt: "+30pt", color: "#ffd54f", bg: "#7c5c00" },
            { label: "単勝30倍超", pt: "+100pt", color: "#ff7043", bg: "#7f1d1d" },
          ].map((t) => (
            <span key={t.label}
              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ color: t.color, backgroundColor: t.bg }}>
              {t.label} {t.pt}
            </span>
          ))}
        </div>

        {/* 直近ログ */}
        {!loading && kreward && kreward.log.length > 0 && (
          <div className="mb-3 space-y-1">
            {kreward.log.slice(0, 5).map((l, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="text-[#666] truncate max-w-[75%]">{l.reason}</span>
                <span className={`font-bold shrink-0 ${l.points > 0 ? "text-[#d4a017]" : "text-[#888]"}`}>
                  {l.points > 0 ? `+${l.points}pt` : `${l.points}pt`}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 近日公開ティーザー */}
        <div className="border-t border-[#f0e0a0] pt-3 flex items-center gap-2 opacity-60">
          <span className="text-[10px] bg-[#888] text-white font-bold px-1.5 py-0.5 rounded shrink-0">近日公開</span>
          <span className="text-[11px] text-[#888]">Kリワードを使った特典機能が近日公開予定です</span>
        </div>
      </div>

      {loading ? (
        <div className="py-10 text-center text-sm text-[#888] animate-pulse">
          読み込み中...
        </div>
      ) : !data || data.total_races === 0 ? (
        <div className="py-10 text-center">
          <div className="text-3xl mb-3">🗳️</div>
          <div className="text-sm font-bold text-[#999] mb-2">
            まだ投票履歴がありません
          </div>
          <div className="text-[11px] text-[#bbb] mb-4">
            レースページの「みんなの予想」から投票してみましょう
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 bg-[#1f7a1f] text-white font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-[#16611a] transition"
          >
            レース一覧へ
          </Link>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className="text-2xl font-black text-[#1f7a1f]">
                {data.total_races}
              </div>
              <div className="text-[10px] text-[#888] mt-1">投票数</div>
            </div>
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className="text-2xl font-black text-[#E53935]">
                {data.hit_rate}%
              </div>
              <div className="text-[10px] text-[#888] mt-1">的中率</div>
            </div>
            <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 text-center shadow-sm">
              <div className={`text-2xl font-black ${data.roi >= 100 ? "text-[#E53935]" : "text-[#333]"}`}>
                {data.roi}%
              </div>
              <div className="text-[10px] text-[#888] mt-1">回収率</div>
            </div>
          </div>

          {/* Breakdown: confirmed vs pending */}
          <div className="flex items-center justify-center gap-3 text-[10px] text-[#888] mb-3">
            <span>確定: <b className="text-[#333]">{data.finalized_count}</b>件</span>
            <span className="text-[#ddd]">|</span>
            <span>結果待ち: <b className="text-[#F57C00]">{data.pending_count}</b>件</span>
            {data.cancelled_count > 0 && (
              <>
                <span className="text-[#ddd]">|</span>
                <span>中止: <b className="text-[#607D8B]">{data.cancelled_count}</b>件</span>
              </>
            )}
          </div>

          {/* Explanation */}
          <div className="bg-[#f8f8f8] border border-dashed border-[#d0d0d0] rounded-lg p-3 mb-5">
            <p className="text-[11px] text-[#888] leading-relaxed">
              回収率は本命馬の単勝100円購入を想定して計算しています。
              的中率・回収率は結果確定済みのレースのみで集計されます。
              {lastUpdated && (
                <span className="block mt-1 text-[10px] text-[#aaa]">
                  最終更新: {formatTime(lastUpdated)}
                </span>
              )}
            </p>
          </div>

          {/* History list */}
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-bold text-[#444]">投票履歴</span>
            <span className="text-[10px] text-[#999]">全{data.total_races}件</span>
          </div>

          <div className="space-y-2">
            {data.history.map((h) => {
              const r = RESULT_LABEL[h.result] || RESULT_LABEL.pending;
              const isHit = h.result === "hit" || h.result === "hit_no_payout";
              const profit = h.result === "hit" && h.payout > 0 ? h.payout - 100 : null;
              return (
                <Link
                  key={h.race_id}
                  href={`/race/${raceIdToPath(h.race_id)}`}
                  className="block bg-white border border-[#d0d0d0] rounded-lg p-3 hover:border-[#1f7a1f] transition shadow-sm"
                  aria-label={`${h.date} ${h.venue} ${h.race_number}R ${h.horse_name} ${r.text}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] text-[#999] shrink-0">{h.date}</span>
                      <span className="text-xs font-bold text-[#333] shrink-0">
                        {h.venue} {h.race_number}R
                      </span>
                      <span className="text-[11px] text-[#666] truncate">{h.race_name}</span>
                    </div>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded shrink-0"
                      style={{ color: r.color, backgroundColor: r.bg }}
                    >
                      {r.text}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#1f7a1f]">
                        {h.horse_number}番
                      </span>
                      <span className="text-sm font-bold text-[#222]">
                        {h.horse_name}
                      </span>
                    </div>
                    <div className="text-right">
                      {h.odds > 0 && (
                        <span className="text-[11px] text-[#888]">
                          {h.odds}倍
                        </span>
                      )}
                      {profit !== null && (
                        <span className="text-xs font-bold text-[#E53935] ml-2">
                          +{profit}円
                        </span>
                      )}
                      {isHit && profit === null && (
                        <span className="text-[10px] font-bold text-[#E53935] ml-2">
                          (配当情報未取得)
                        </span>
                      )}
                      {h.result === "cancelled" && (
                        <span className="text-[10px] text-[#607D8B] ml-2">
                          投票無効・返還
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
