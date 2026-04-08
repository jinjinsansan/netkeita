"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ArticleEditor from "@/components/ArticleEditor";
import AdminGate from "@/components/AdminGate";
import AuthGuard from "@/components/AuthGuard";
import { ToastStack, nextToastId, type ToastMessage } from "@/components/Toast";
import type { Article, ArticleInput } from "@/lib/api";
import { fetchArticle, updateArticle, deleteArticle } from "@/lib/api";

export default function EditArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  return (
    <AuthGuard>
      <AdminGate>
        <EditArticleForm slug={slug} />
      </AdminGate>
    </AuthGuard>
  );
}

function EditArticleForm({ slug }: { slug: string }) {
  const router = useRouter();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = (kind: ToastMessage["kind"], text: string) => {
    setToasts((prev) => [...prev, { id: nextToastId(), kind, text }]);
  };
  const dismissToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const data = await fetchArticle(slug);
      if (cancelled) return;
      setArticle(data);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const handleSubmit = async (input: ArticleInput) => {
    setSubmitting(true);
    const res = await updateArticle(slug, input);
    if (res.success) {
      pushToast(
        "success",
        input.status === "draft" ? "下書きを更新しました" : "記事を更新しました"
      );
      setTimeout(() => {
        router.push(`/articles/${encodeURIComponent(res.article.slug)}`);
        router.refresh();
      }, 600);
    } else {
      if (res.conflict) {
        pushToast(
          "error",
          "別の管理者によって更新されています。ページを再読み込みしてください。"
        );
      } else {
        pushToast("error", res.error || "更新に失敗しました");
      }
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    setSubmitting(true);
    const res = await deleteArticle(slug);
    if (res.success) {
      pushToast("success", "記事を削除しました");
      setTimeout(() => {
        router.push("/articles");
        router.refresh();
      }, 600);
    } else {
      pushToast("error", res.error || "削除に失敗しました");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center text-sm text-[#888] animate-pulse">
        読み込み中...
      </div>
    );
  }

  if (!article) {
    return (
      <div className="max-w-[960px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#c62828]">記事が見つかりません</div>
      </div>
    );
  }

  const initial: Partial<ArticleInput> = {
    title: article.title,
    description: article.description,
    body: article.body,
    thumbnail_url: article.thumbnail_url,
    status: article.status,
    slug: article.slug,
    race_id: article.race_id,
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6">
      <ArticleEditor
        autosaveKey={`edit:${slug}`}
        initial={initial}
        expectedUpdatedAt={article.updated_at}
        submitting={submitting}
        submitLabel="更新"
        showDelete
        slugEditable={false}
        onSubmit={handleSubmit}
        onDelete={handleDelete}
        onCancel={() => router.push(`/articles/${encodeURIComponent(slug)}`)}
      />
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
