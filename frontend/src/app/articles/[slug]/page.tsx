import type { Metadata } from "next";
import ArticleDetailView from "./ArticleDetailView";
import { SITE_URL } from "@/lib/site";
import type { Article } from "@/lib/api";

const API_URL = "https://bot.dlogicai.in/nk";

// Cache articles at the edge for 60 seconds so viral shares don't hammer
// the backend. Admin-facing draft views bypass this because client-side
// fetchArticle uses cache: "no-store".
const REVALIDATE_SECONDS = 60;

async function fetchArticleServer(slug: string): Promise<Article | null> {
  try {
    const res = await fetch(
      `${API_URL}/api/articles/${encodeURIComponent(slug)}`,
      { next: { revalidate: REVALIDATE_SECONDS } }
    );
    if (!res.ok) return null;
    return (await res.json()) as Article;
  } catch {
    return null;
  }
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticleServer(slug);
  if (!article) {
    return {
      title: "記事が見つかりません | netkeita",
      robots: { index: false, follow: false },
    };
  }

  const url = `${SITE_URL}/articles/${encodeURIComponent(slug)}`;
  const title = `${article.title} | netkeita`;
  const description = article.description || article.title;
  const image = article.thumbnail_url
    ? {
        url: article.thumbnail_url,
        width: 1200,
        height: 630,
        alt: article.title,
      }
    : undefined;

  // Drafts should never be indexed even if a crawler stumbles on the URL.
  const isDraft = article.status !== "published";

  return {
    title,
    description,
    alternates: { canonical: url },
    robots: isDraft
      ? { index: false, follow: false }
      : { index: true, follow: true },
    openGraph: {
      title,
      description,
      url,
      siteName: "netkeita",
      type: "article",
      locale: "ja_JP",
      images: image ? [image] : undefined,
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title,
      description,
      images: image ? [image.url] : undefined,
    },
  };
}

export default async function ArticleDetailPage(
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  // Fetch once on the server and forward to the Client Component via props.
  // This eliminates the previous "fetch in generateMetadata + fetch in
  // useEffect" duplication, halving backend load per article view.
  const initialArticle = await fetchArticleServer(slug);
  return <ArticleDetailView slug={slug} initialArticle={initialArticle} />;
}
