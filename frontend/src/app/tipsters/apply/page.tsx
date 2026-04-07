"use client";

import { useState } from "react";
import Link from "next/link";
import { useEffect } from "react";
import { applyAsTipster, fetchMyTipsterProfile } from "@/lib/api";
import type { TipsterProfile } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";

export default function TipsterApplyPage() {
  return (
    <AuthGuard>
      <ApplyForm />
    </AuthGuard>
  );
}

function ApplyForm() {
  const [existing, setExisting] = useState<TipsterProfile | null | undefined>(undefined);
  const [catchphrase, setCatchphrase] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchMyTipsterProfile().then((p) => setExisting(p));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catchphrase.trim()) {
      setError("キャッチフレーズを入力してください");
      return;
    }
    setSubmitting(true);
    setError(null);
    const res = await applyAsTipster(catchphrase.trim(), description.trim());
    if (res.success) {
      setSuccess(true);
    } else {
      setError(res.error || "申請に失敗しました");
    }
    setSubmitting(false);
  };

  if (existing === undefined) {
    return <div className="max-w-[600px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">読み込み中...</div>;
  }

  if (existing?.status === "approved") {
    return (
      <div className="max-w-[600px] mx-auto px-4 py-10 text-center">
        <div className="text-2xl mb-3">✅</div>
        <p className="text-sm font-bold text-[#1f7a1f] mb-4">すでに承認済みの予想家です</p>
        <Link href="/predictions/new" className="text-xs font-bold text-white bg-[#1f7a1f] px-4 py-2 rounded-lg">
          予想を投稿する
        </Link>
      </div>
    );
  }

  if (existing?.status === "pending" || success) {
    return (
      <div className="max-w-[600px] mx-auto px-4 py-10 text-center">
        <div className="text-2xl mb-3">📩</div>
        <p className="text-sm font-bold text-[#222] mb-2">申請を受け付けました</p>
        <p className="text-xs text-[#666]">管理者が確認後、承認をお知らせします。</p>
        <Link href="/" className="mt-4 inline-block text-xs font-bold text-[#1f7a1f] hover:underline">
          トップへ戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[600px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <Link href="/tipsters" className="text-[#1565C0] hover:underline font-bold">予想家</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>申請</span>
      </div>

      <h1 className="text-xl font-black text-[#222] mb-1">予想家に申請</h1>
      <p className="text-xs text-[#666] mb-6">
        管理者が内容を確認し、承認後に予想を投稿できるようになります。
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            キャッチフレーズ <span className="text-[#c62828]">*</span>
          </label>
          <input
            type="text"
            value={catchphrase}
            onChange={(e) => setCatchphrase(e.target.value.slice(0, 60))}
            placeholder="例: ダートグレードで直近1年プラス収支を実現"
            maxLength={60}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
          <p className="text-[10px] text-[#999] mt-0.5">{catchphrase.length} / 60</p>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            自己紹介 (任意)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value.slice(0, 400))}
            placeholder="得意なレースや予想スタイルを紹介してください"
            rows={4}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
          <p className="text-[10px] text-[#999] mt-0.5">{description.length} / 400</p>
        </div>

        {error && (
          <div className="rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-[#1f7a1f] hover:bg-[#16611a] text-white font-bold text-sm py-3 rounded-lg transition disabled:opacity-50"
        >
          {submitting ? "送信中..." : "申請する"}
        </button>
      </form>
    </div>
  );
}
