"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchArticlePage } from "@/lib/api";
import type { ArticleListResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import ArticleCard from "@/components/ArticleCard";

const PAGE_SIZE = 24;

export default function ArticlesPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  const [page, setPage] = useState<ArticleListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [includeDrafts, setIncludeDrafts] = useState(false);
  const [offset, setOffset] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchArticlePage({
      includeDrafts: isAdmin && includeDrafts,
      limit: PAGE_SIZE,
      offset,
    });
    setPage(data);
    setLoading(false);
  }, [isAdmin, includeDrafts, offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data-fetch pattern (codebase convention)
    load();
  }, [load]);

  // Reset pagination whenever filters change.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset on filter change
    setOffset(0);
  }, [includeDrafts, isAdmin]);

  const articles = page?.articles || [];
  const totalCount = page?.total_count || 0;
  const hasMore = page?.has_more || false;
  const currentPageNum = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  return (
    <div className="max-w-[960px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>記事</span>
      </div>

      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-black text-[#222]">記事</h1>
          {totalCount > 0 && (
            <span className="text-[11px] text-[#999]">
              全{totalCount}件
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <label className="flex items-center gap-1 text-[11px] text-[#666] select-none">
                <input
                  type="checkbox"
                  checked={includeDrafts}
                  onChange={(e) => setIncludeDrafts(e.target.checked)}
                />
                下書きも表示
              </label>

            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white border border-[#e5e5e5] rounded-lg overflow-hidden animate-pulse"
            >
              <div className="aspect-[16/9] bg-[#f0f0f0]" />
              <div className="p-3 space-y-2">
                <div className="h-3 bg-[#f0f0f0] rounded w-1/3" />
                <div className="h-4 bg-[#f0f0f0] rounded w-5/6" />
                <div className="h-3 bg-[#f0f0f0] rounded w-2/3" />
              </div>
            </div>
          ))}
        </div>
      ) : articles.length === 0 ? (
        <div className="py-10 text-center">
          <div className="text-3xl mb-3">📝</div>
          <div className="text-sm font-bold text-[#999]">
            まだ記事がありません
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {articles.map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-3">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                ← 前へ
              </button>
              <span className="text-[11px] text-[#666]">
                {currentPageNum} / {totalPages}
              </span>
              <button
                type="button"
                disabled={!hasMore}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                次へ →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
