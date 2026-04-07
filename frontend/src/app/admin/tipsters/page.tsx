"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchPendingTipsters,
  fetchTipsters,
  adminApproveTipster,
  adminRejectTipster,
  adminDeleteTipster,
  adminGrantPremium,
  adminRevokePremium,
} from "@/lib/api";
import type { TipsterProfile } from "@/lib/api";
import AdminGate from "@/components/AdminGate";
import AuthGuard from "@/components/AuthGuard";

export default function AdminTipstersPage() {
  return (
    <AuthGuard>
      <AdminGate>
        <AdminTipstersContent />
      </AdminGate>
    </AuthGuard>
  );
}

function AdminTipstersContent() {
  const [pending, setPending] = useState<TipsterProfile[]>([]);
  const [approved, setApproved] = useState<TipsterProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [premiumUserId, setPremiumUserId] = useState("");
  const [premiumMsg, setPremiumMsg] = useState<string | null>(null);

  const reload = () => {
    Promise.all([fetchPendingTipsters(), fetchTipsters()]).then(([pend, appr]) => {
      setPending(pend);
      setApproved(appr);
      setLoading(false);
    });
  };

  useEffect(() => { reload(); }, []);

  const handleApprove = async (id: string) => {
    const res = await adminApproveTipster(id);
    setActionMsg(res.success ? "承認しました" : res.error || "エラー");
    reload();
  };

  const handleReject = async (id: string) => {
    if (!confirm("却下しますか？")) return;
    const res = await adminRejectTipster(id);
    setActionMsg(res.success ? "却下しました" : res.error || "エラー");
    reload();
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`「${name}」を削除しますか？この操作は取り消せません。`)) return;
    const res = await adminDeleteTipster(id);
    setActionMsg(res.success ? `${name} を削除しました` : res.error || "エラー");
    reload();
  };

  const handleGrantPremium = async () => {
    if (!premiumUserId.trim()) return;
    const res = await adminGrantPremium(premiumUserId.trim());
    setPremiumMsg(res.success ? `${premiumUserId} にプレミアムアクセスを付与しました` : res.error || "エラー");
    setPremiumUserId("");
  };

  const handleRevokePremium = async () => {
    if (!premiumUserId.trim()) return;
    const res = await adminRevokePremium(premiumUserId.trim());
    setPremiumMsg(res.success ? `${premiumUserId} のプレミアムアクセスを取消しました` : res.error || "エラー");
    setPremiumUserId("");
  };

  return (
    <div className="max-w-[800px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>管理: 予想家審査</span>
      </div>

      <h1 className="text-lg font-black text-[#222] mb-5">予想家審査</h1>

      {actionMsg && (
        <div className="mb-4 rounded-lg bg-[#e8f5e9] border border-[#a5d6a7] px-3 py-2 text-xs text-[#1f7a1f] font-bold">
          {actionMsg}
        </div>
      )}

      {/* Pending applications */}
      <h2 className="text-sm font-black text-[#444] mb-3">申請中 ({pending.length}件)</h2>
      {loading ? (
        <p className="text-sm text-[#888] animate-pulse">読み込み中...</p>
      ) : pending.length === 0 ? (
        <p className="text-sm text-[#999] mb-8">申請中の予想家はいません</p>
      ) : (
        <div className="space-y-3 mb-8">
          {pending.map((t) => (
            <div key={t.line_user_id} className="border border-[#d0d0d0] rounded-lg p-4 bg-white">
              <div className="flex items-start gap-3">
                {t.picture_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={t.picture_url} alt={t.display_name} className="w-12 h-12 rounded-full object-cover shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-[#e0e0e0] flex items-center justify-center text-lg font-bold text-[#888] shrink-0">
                    {t.display_name[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-[#222]">{t.display_name}</p>
                  <p className="text-[11px] text-[#666] mt-0.5">ID: {t.line_user_id}</p>
                  <p className="text-xs text-[#f57c00] font-bold mt-1">{t.catchphrase}</p>
                  {t.description && (
                    <p className="text-[11px] text-[#555] mt-1">{t.description}</p>
                  )}
                  <p className="text-[10px] text-[#999] mt-1">申請日: {t.applied_at?.slice(0, 10)}</p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleApprove(t.line_user_id)}
                    className="text-xs font-bold text-white bg-[#1f7a1f] hover:bg-[#16611a] px-3 py-1.5 rounded transition"
                  >
                    承認
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReject(t.line_user_id)}
                    className="text-xs font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-3 py-1.5 rounded transition"
                  >
                    却下
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Premium access management */}
      {/* Approved tipsters */}
      <h2 className="text-sm font-black text-[#444] mb-3">承認済み ({approved.length}件)</h2>
      {approved.length === 0 ? (
        <p className="text-sm text-[#999] mb-8">承認済みの予想家はいません</p>
      ) : (
        <div className="space-y-3 mb-8">
          {approved.map((t) => (
            <div key={t.line_user_id} className="border border-[#c8e6c9] rounded-lg p-4 bg-white">
              <div className="flex items-center gap-3">
                {t.picture_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={t.picture_url} alt={t.display_name} className="w-10 h-10 rounded-full object-cover shrink-0" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-[#e0e0e0] flex items-center justify-center text-base font-bold text-[#888] shrink-0">
                    {t.display_name[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-[#222]">{t.display_name}</p>
                  <p className="text-[11px] text-[#f57c00] truncate">{t.catchphrase}</p>
                  <p className="text-[10px] text-[#999]">ID: {t.line_user_id}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(t.line_user_id, t.display_name)}
                  className="shrink-0 text-xs font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-3 py-1.5 rounded transition"
                >
                  削除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-sm font-black text-[#444] mb-3">プレミアムアクセス管理</h2>
      <div className="border border-[#d0d0d0] rounded-lg p-4 bg-white">
        <p className="text-[11px] text-[#666] mb-3">
          LINE User ID を入力して有料予想へのアクセス権を付与・取消します。
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={premiumUserId}
            onChange={(e) => setPremiumUserId(e.target.value)}
            placeholder="Uxxxxxxxxxxxxxxxxxx"
            className="flex-1 border border-[#d0d0d0] rounded px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#1f7a1f]"
          />
          <button
            type="button"
            onClick={handleGrantPremium}
            className="text-xs font-bold text-white bg-[#d4a017] hover:bg-[#b8860b] px-3 py-2 rounded transition"
          >
            付与
          </button>
          <button
            type="button"
            onClick={handleRevokePremium}
            className="text-xs font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-3 py-2 rounded transition"
          >
            取消
          </button>
        </div>
        {premiumMsg && (
          <p className="mt-2 text-[11px] text-[#1f7a1f] font-bold">{premiumMsg}</p>
        )}
      </div>
    </div>
  );
}
