"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import ArticleEditor from "@/components/ArticleEditor";
import AuthGuard from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { createArticle } from "@/lib/api";
import type { ArticleInput } from "@/lib/api";

export default function NewFeaturePage() {
  return (
    <AuthGuard>
      <NewFeatureForm />
    </AuthGuard>
  );
}

function NewFeatureForm() {
  const router = useRouter();
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user && !user.is_admin) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-10 text-center">
        <div className="text-sm font-bold text-[#c62828] mb-4">
          管理者のみアクセスできます
        </div>
        <Link href="/" className="text-xs font-bold text-[#1f7a1f] hover:underline">
          ← トップへ戻る
        </Link>
      </div>
    );
  }

  const handleSubmit = async (input: ArticleInput) => {
    setSubmitting(true);
    setError(null);
    const res = await createArticle({ ...input, content_type: "feature" });
    setSubmitting(false);
    if (!res.success) {
      setError(res.error);
      return;
    }
    router.push(`/articles/${encodeURIComponent(res.article.slug)}`);
  };

  return (
    <div className="max-w-[800px] mx-auto px-4 py-6">
      <div className="text-[11px] text-[#666] mb-3 font-medium">
        <Link href="/" className="text-[#1565C0] hover:underline font-bold">
          レース一覧
        </Link>
        <span className="mx-1 text-[#999]">&gt;</span>
        <span>特集ページ作成</span>
      </div>
      <div className="mb-6">
        <h1 className="text-2xl font-black text-[#1a1a1a] mb-1">特集ページ作成</h1>
        <p className="text-xs text-[#888]">
          管理者のみ。公開するとTOPページの「特集」セクションに表示されます。
        </p>
      </div>
      {error && (
        <div
          className="mb-3 rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]"
          role="alert"
        >
          {error}
        </div>
      )}
      <ArticleEditor
        autosaveKey="feature-new"
        submitLabel={submitting ? "公開中..." : "特集を公開"}
        submitting={submitting}
        onSubmit={handleSubmit}
        onCancel={() => router.back()}
      />
    </div>
  );
}
