import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Next.js regenerates the sitemap per request; cap the remote fetch so a
// slow/unhealthy API never holds up the whole SEO surface.
const API_URL = "https://bot.dlogicai.in/nk";
const REMOTE_TIMEOUT_MS = 5000;

interface RemoteArticleSummary {
  slug: string;
  updated_at?: string;
  status?: string;
}

async function fetchPublishedArticles(): Promise<RemoteArticleSummary[]> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REMOTE_TIMEOUT_MS);
    const res = await fetch(`${API_URL}/api/articles?limit=100`, {
      // Re-cache for an hour so we don't hammer the API on every crawl.
      next: { revalidate: 3600 },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return [];
    const data = await res.json();
    const items: RemoteArticleSummary[] = Array.isArray(data?.articles) ? data.articles : [];
    return items.filter((a) => a.status === "published");
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  // Static routes visible to anonymous users. Private routes (/mypage,
  // /articles/new, /articles/[slug]/edit) are deliberately excluded.
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: `${SITE_URL}/`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/articles`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/login`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.3,
    },
  ];

  const articles = await fetchPublishedArticles();
  const articleRoutes: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${SITE_URL}/articles/${encodeURIComponent(a.slug)}`,
    lastModified: a.updated_at ? new Date(a.updated_at) : now,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  return [...staticRoutes, ...articleRoutes];
}
