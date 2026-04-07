"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  fetchMyTipsterProfile,
  fetchTipster,
  deleteArticle,
  uploadArticleImage,
} from "@/lib/api";
import type { TipsterProfile, ArticleSummary } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";

export default function TipsterDashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { user, refresh } = useAuth();
  const router = useRouter();

  const [profile, setProfile] = useState<TipsterProfile | null>(null);
  const [predictions, setPredictions] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [notTipster, setNotTipster] = useState(false);

  // Profile edit state
  const [editMode, setEditMode] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [catchphrase, setCatchphrase] = useState("");
  const [description, setDescription] = useState("");
  const [pictureUrl, setPictureUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const API_URL = "https://bot.dlogicai.in/nk";

  const load = async () => {
    const p = await fetchMyTipsterProfile();
    if (!p || p.status !== "approved") {
      setNotTipster(true);
      setLoading(false);
      return;
    }
    setProfile(p);
    setDisplayName(p.display_name || "");
    setCatchphrase(p.catchphrase || "");
    setDescription(p.description || "");
    setPictureUrl(p.picture_url || "");

    const data = await fetchTipster(p.line_user_id);
    setPredictions(data?.predictions || []);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleSaveProfile = async () => {
    if (!profile) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const token = localStorage.getItem("nk_token");
      const res = await fetch(`${API_URL}/api/tipsters/me`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ display_name: displayName, catchphrase, description, picture_url: pictureUrl }),
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data.profile);
        setEditMode(false);
        setSaveMsg("プロフィールを更新しました");
        refresh();
      } else {
        setSaveMsg("更新に失敗しました");
      }
    } catch {
      setSaveMsg("通信エラーが発生しました");
    }
    setSaving(false);
  };

  const handleIconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const res = await uploadArticleImage(file);
    if (res.success && res.url) {
      setPictureUrl(res.url);
    } else {
      setSaveMsg(res.error || "アップロードに失敗しました");
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDelete = async (slug: string, title: string) => {
    if (!confirm(`「${title}」を削除しますか？`)) return;
    const res = await deleteArticle(slug);
    if (res.success) {
      setPredictions((prev) => prev.filter((p) => p.slug !== slug));
    } else {
      alert(res.error || "削除に失敗しました");
    }
  };

  if (loading) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">
        読み込み中...
      </div>
    );
  }

  if (notTipster) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10 text-center">
        <p className="text-sm font-bold text-[#c62828] mb-4">承認済みの予想家のみアクセスできます</p>
        <Link href="/tipsters/apply" className="text-xs font-bold text-[#1f7a1f] hover:underline">
          予想家に申請する
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[720px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>予想家ダッシュボード</span>
      </div>

      <h1 className="text-xl font-black text-[#222] mb-5">予想家ダッシュボード</h1>

      {saveMsg && (
        <div className="mb-4 rounded-lg bg-[#e8f5e9] border border-[#a5d6a7] px-3 py-2 text-xs text-[#1f7a1f] font-bold">
          {saveMsg}
        </div>
      )}

      {/* Profile section */}
      <div className="border border-[#d0d0d0] rounded-lg bg-white p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-black text-[#444]">プロフィール</h2>
          {!editMode ? (
            <button
              type="button"
              onClick={() => setEditMode(true)}
              className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-1.5 rounded transition"
            >
              編集
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setEditMode(false); setSaveMsg(null); }}
                className="text-xs font-bold text-[#666] border border-[#ccc] hover:bg-[#f5f5f5] px-3 py-1.5 rounded transition"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleSaveProfile}
                disabled={saving}
                className="text-xs font-bold text-white bg-[#1f7a1f] hover:bg-[#16611a] px-3 py-1.5 rounded transition disabled:opacity-50"
              >
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          )}
        </div>

        {!editMode ? (
          <div className="flex items-start gap-4">
            {profile?.picture_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={profile.picture_url} alt="" className="w-16 h-16 rounded-full object-cover bg-[#eee] shrink-0" />
            ) : (
              <div className="w-16 h-16 rounded-full bg-[#e0e0e0] flex items-center justify-center text-2xl font-bold text-[#888] shrink-0">
                {profile?.display_name[0]}
              </div>
            )}
            <div>
              <p className="text-base font-bold text-[#222]">{profile?.display_name}</p>
              <p className="text-xs text-[#f57c00] font-bold mt-1">{profile?.catchphrase || "（未設定）"}</p>
              <p className="text-sm text-[#555] mt-1 leading-relaxed">{profile?.description || "（未設定）"}</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Icon */}
            <div>
              <label className="block text-[11px] font-bold text-[#444] mb-1">アイコン画像</label>
              <div className="flex items-center gap-3">
                {pictureUrl ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={pictureUrl} alt="" className="w-14 h-14 rounded-full object-cover bg-[#eee] shrink-0" />
                ) : (
                  <div className="w-14 h-14 rounded-full bg-[#e0e0e0] flex items-center justify-center text-xl font-bold text-[#888] shrink-0">
                    {profile?.display_name[0]}
                  </div>
                )}
                <div className="flex-1 space-y-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="text-xs font-bold bg-[#1f7a1f] hover:bg-[#16611a] text-white px-3 py-1.5 rounded transition disabled:opacity-50"
                  >
                    {uploading ? "アップロード中..." : "画像を選択"}
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleIconUpload} className="hidden" />
                  <input
                    type="url"
                    value={pictureUrl}
                    onChange={(e) => setPictureUrl(e.target.value)}
                    placeholder="または画像URLを直接入力"
                    className="w-full border border-[#d0d0d0] rounded px-2 py-1 text-xs focus:outline-none focus:border-[#1f7a1f]"
                  />
                </div>
              </div>
            </div>

            {/* Display name */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-bold text-[#444]">表示名</label>
                <span className="text-[10px] text-[#999]">{displayName.length} / 50</span>
              </div>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value.slice(0, 50))}
                placeholder="予想家としての名前"
                className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
              />
            </div>

            {/* Catchphrase */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-bold text-[#444]">キャッチフレーズ</label>
                <span className="text-[10px] text-[#999]">{catchphrase.length} / 60</span>
              </div>
              <input
                type="text"
                value={catchphrase}
                onChange={(e) => setCatchphrase(e.target.value.slice(0, 60))}
                placeholder="例: ダートグレードで直近1年プラス収支を実現"
                className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
              />
            </div>

            {/* Description */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] font-bold text-[#444]">自己紹介</label>
                <span className="text-[10px] text-[#999]">{description.length} / 400</span>
              </div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, 400))}
                placeholder="得意なレースや予想スタイルを紹介してください"
                rows={4}
                className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
              />
            </div>
          </div>
        )}
      </div>

      {/* Predictions section */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-black text-[#444]">
          投稿した予想
          <span className="text-[11px] font-normal text-[#999] ml-2">{predictions.length}件</span>
        </h2>
        <Link
          href="/predictions/new"
          className="text-xs font-bold text-white bg-[#1f7a1f] hover:bg-[#16611a] px-3 py-2 rounded-lg transition"
        >
          + 新規投稿
        </Link>
      </div>

      {predictions.length === 0 ? (
        <div className="py-8 text-center border border-[#e5e5e5] rounded-lg bg-white">
          <p className="text-sm text-[#999] mb-3">まだ予想を投稿していません</p>
          <Link
            href="/predictions/new"
            className="text-xs font-bold text-[#1f7a1f] hover:underline"
          >
            最初の予想を投稿する →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {predictions.map((p) => (
            <div key={p.slug} className="border border-[#d0d0d0] rounded-lg bg-white p-3 flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  {p.status === "draft" && (
                    <span className="text-[9px] font-bold text-[#F57C00] bg-[#fff3e0] px-1.5 py-0.5 rounded">下書き</span>
                  )}
                  {p.is_premium && (
                    <span className="text-[9px] font-bold text-white bg-[#d4a017] px-1.5 py-0.5 rounded">有料</span>
                  )}
                  <span className="text-[10px] text-[#999]">{formatDate(p.created_at)}</span>
                </div>
                <p className="text-sm font-bold text-[#222] truncate">{p.title}</p>
                {p.bet_method && (
                  <p className="text-[11px] text-[#666] mt-0.5">
                    {p.bet_method}{p.ticket_count ? ` / ${p.ticket_count}点` : ""}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <Link
                  href={`/predictions/${encodeURIComponent(p.slug)}/edit`}
                  className="text-[10px] font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-2 py-1 rounded transition"
                >
                  編集
                </Link>
                <button
                  type="button"
                  onClick={() => handleDelete(p.slug, p.title)}
                  className="text-[10px] font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-2 py-1 rounded transition"
                >
                  削除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-[#e5e5e5]">
        <Link
          href={`/tipsters/${encodeURIComponent(profile?.line_user_id || "")}`}
          className="text-xs text-[#1565C0] hover:underline font-bold"
        >
          公開プロフィールを見る →
        </Link>
      </div>
    </div>
  );
}
