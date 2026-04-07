"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchTipster, fetchPremiumStatus } from "@/lib/api";
import type { TipsterProfile, ArticleSummary } from "@/lib/api";
import PredictionCard from "@/components/PredictionCard";
import { useAuth } from "@/lib/auth-context";

export default function TipsterPage() {
  const params = useParams();
  const id = decodeURIComponent(params.id as string);
  const { user } = useAuth();

  const [profile, setProfile] = useState<TipsterProfile | null>(null);
  const [predictions, setPredictions] = useState<ArticleSummary[]>([]);
  const [hasPremium, setHasPremium] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    Promise.all([fetchTipster(id), user ? fetchPremiumStatus() : Promise.resolve(false)]).then(
      ([data, premium]) => {
        if (!data) {
          setNotFound(true);
        } else {
          setProfile(data.profile);
          setPredictions(data.predictions);
        }
        setHasPremium(!!premium || !!user?.is_admin);
        setLoading(false);
      }
    );
  }, [id, user]);

  if (loading) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10">
        <div className="animate-pulse space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-[#eee]" />
            <div className="space-y-2 flex-1">
              <div className="h-5 bg-[#eee] rounded w-1/3" />
              <div className="h-3 bg-[#eee] rounded w-1/2" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (notFound || !profile) {
    return (
      <div className="max-w-[720px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#999] mb-4">予想家が見つかりません</div>
        <Link href="/tipsters" className="text-xs font-bold text-[#1f7a1f] hover:underline">
          ← 予想家一覧へ
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[720px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">レース一覧</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <Link href="/tipsters" className="text-[#1565C0] hover:underline font-bold">予想家</Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>{profile.display_name}</span>
      </div>

      {/* Profile card */}
      <div className="border border-[#d0d0d0] rounded-lg bg-white p-5 mb-6">
        <div className="flex items-start gap-4">
          {profile.picture_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={profile.picture_url}
              alt={profile.display_name}
              className="w-16 h-16 rounded-full object-cover bg-[#eee] shrink-0"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-[#e0e0e0] flex items-center justify-center text-2xl font-bold text-[#888] shrink-0">
              {profile.display_name[0]}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-black text-[#222]">{profile.display_name}</h1>
            {profile.catchphrase && (
              <p className="text-xs font-bold text-[#f57c00] mt-1">{profile.catchphrase}</p>
            )}
            {profile.description && (
              <p className="text-sm text-[#555] mt-2 leading-relaxed">{profile.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Predictions */}
      <h2 className="text-base font-black text-[#222] mb-3">
        予想一覧
        {predictions.length > 0 && (
          <span className="text-[11px] font-normal text-[#999] ml-2">{predictions.length}件</span>
        )}
      </h2>

      {predictions.length === 0 ? (
        <div className="py-8 text-center text-sm text-[#999]">まだ予想が投稿されていません</div>
      ) : (
        <div className="space-y-3">
          {predictions.map((p) => (
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
