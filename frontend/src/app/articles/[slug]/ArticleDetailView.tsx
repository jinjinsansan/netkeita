"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { fetchArticle, deleteArticle } from "@/lib/api";
import type { Article } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import ShareButton from "@/components/ShareButton";
import ConfirmModal from "@/components/ConfirmModal";
import { SITE_URL } from "@/lib/site";
import { formatDate } from "@/lib/format";

export default function ArticleDetailView({
  slug,
  initialArticle,
}: {
  slug: string;
  initialArticle: Article | null;
}) {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;

  // Seed from the server-rendered article so there's no "読み込み中..." flash
  // for the common case. We only re-fetch client-side when the admin flag
  // flips (so drafts become visible) or when the initial fetch returned null.
  const [article, setArticle] = useState<Article | null>(initialArticle);
  const [loading, setLoading] = useState(initialArticle === null);
  const [notFound, setNotFound] = useState(initialArticle === null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Client-side refetch triggers:
  //  1. The SSR fetch returned null AND we're an admin — maybe it was a
  //     draft that SSR couldn't see because it had no cookie.
  //  2. The slug prop changes (route navigation).
  useEffect(() => {
    if (article && article.slug === slug) return;
    if (!isAdmin && article === null && !initialArticle) {
      // Public user and SSR already said 404 — don't bother refetching.
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      const data = await fetchArticle(slug);
      if (cancelled) return;
      if (!data) {
        setNotFound(true);
        setArticle(null);
      } else {
        setArticle(data);
        setNotFound(false);
      }
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, isAdmin]);

  const handleDelete = async () => {
    setConfirmDeleteOpen(false);
    setDeleting(true);
    setError(null);
    const res = await deleteArticle(slug);
    if (res.success) {
      router.push("/articles");
      router.refresh();
    } else {
      setError(res.error || "削除に失敗しました");
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-10">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-[#eee] rounded w-2/3" />
          <div className="h-4 bg-[#eee] rounded w-full" />
          <div className="h-4 bg-[#eee] rounded w-5/6" />
          <div className="h-4 bg-[#eee] rounded w-4/6" />
        </div>
      </div>
    );
  }

  if (notFound || !article) {
    return (
      <div className="max-w-[680px] mx-auto px-4 py-10 text-center">
        <div className="text-3xl mb-3">📄</div>
        <div className="text-sm font-bold text-[#999] mb-4">
          記事が見つかりません
        </div>
        <Link
          href="/articles"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1f7a1f] hover:underline"
        >
          記事一覧へ戻る
        </Link>
      </div>
    );
  }

  const publicUrl = `${SITE_URL}/articles/${encodeURIComponent(slug)}`;
  const isDraft = article.status !== "published";
  const readingTime = article.reading_time_minutes;

  return (
    <article className="max-w-[680px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-4 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <Link href="/articles" className="text-[#1565C0] hover:underline font-bold">
          記事
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span className="truncate">{article.title}</span>
      </div>

      {isDraft && (
        <div className="mb-3 rounded-lg bg-[#fff3e0] border border-[#F57C00] px-3 py-2 text-xs text-[#F57C00] font-bold">
          下書き — 一般公開されていません
        </div>
      )}

      {article.thumbnail_url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={article.thumbnail_url}
          alt={article.title}
          className="w-full aspect-[16/9] object-cover rounded-lg mb-5 bg-[#f5f5f5]"
        />
      )}

      <h1 className="text-2xl font-black text-[#1a1a1a] leading-tight mb-3">
        {article.title}
      </h1>

      {article.description && (
        <p className="text-sm text-[#555] leading-relaxed mb-4">
          {article.description}
        </p>
      )}

      <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#e5e5e5]">
        <div className="flex items-center gap-2 text-[11px] text-[#888] flex-wrap">
          {article.author && <span className="font-bold text-[#444]">{article.author}</span>}
          <span className="text-[#ccc]">|</span>
          <span>{formatDate(article.created_at)}</span>
          {article.updated_at && article.updated_at !== article.created_at && (
            <>
              <span className="text-[#ccc]">|</span>
              <span>更新: {formatDate(article.updated_at)}</span>
            </>
          )}
          {readingTime && readingTime > 0 && (
            <>
              <span className="text-[#ccc]">|</span>
              <span>{readingTime}分で読める</span>
            </>
          )}
        </div>
        {isAdmin && (
          <div className="flex items-center gap-2 shrink-0">
            <Link
              href={`/articles/${encodeURIComponent(slug)}/edit`}
              className="text-[10px] font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-2.5 py-1 rounded transition"
            >
              編集
            </Link>
            <button
              type="button"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={deleting}
              className="text-[10px] font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-2.5 py-1 rounded transition disabled:opacity-40"
            >
              削除
            </button>
          </div>
        )}
      </div>

      <div className="prose-nk">
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{article.body}</ReactMarkdown>
      </div>

      {error && (
        <div
          className="mt-4 rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="mt-10 pt-6 border-t border-[#e5e5e5] flex items-center justify-between">
        <ShareButton title={article.title} url={publicUrl} />
        <Link
          href="/articles"
          className="text-xs font-bold text-[#666] hover:text-[#1f7a1f] transition"
        >
          ← 記事一覧
        </Link>
      </div>

      <ConfirmModal
        open={confirmDeleteOpen}
        title="記事を削除"
        message="この記事を完全に削除します。この操作は取り消せません。"
        confirmLabel="削除する"
        danger
        onConfirm={handleDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </article>
  );
}
