"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ArticleEditor from "@/components/ArticleEditor";
import AdminGate from "@/components/AdminGate";
import AuthGuard from "@/components/AuthGuard";
import { ToastStack, nextToastId, type ToastMessage } from "@/components/Toast";
import type { ArticleInput } from "@/lib/api";
import { createArticle } from "@/lib/api";

export default function NewArticlePage() {
  return (
    <AuthGuard>
      <AdminGate>
        <NewArticleForm />
      </AdminGate>
    </AuthGuard>
  );
}

function NewArticleForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = (kind: ToastMessage["kind"], text: string) => {
    setToasts((prev) => [...prev, { id: nextToastId(), kind, text }]);
  };
  const dismissToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleSubmit = async (input: ArticleInput) => {
    setSubmitting(true);
    const res = await createArticle(input);
    if (res.success) {
      pushToast(
        "success",
        input.status === "draft" ? "下書きを保存しました" : "記事を公開しました"
      );
      // Give the toast a moment to show before navigating
      setTimeout(() => {
        router.push(`/articles/${encodeURIComponent(res.article.slug)}`);
        router.refresh();
      }, 600);
    } else {
      pushToast("error", res.error || "作成に失敗しました");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6">
      <ArticleEditor
        autosaveKey="new"
        submitting={submitting}
        submitLabel="公開"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/articles")}
      />
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
