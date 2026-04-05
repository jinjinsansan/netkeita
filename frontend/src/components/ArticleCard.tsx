import Link from "next/link";
import type { ArticleSummary } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function ArticleCard({ article }: { article: ArticleSummary }) {
  const isDraft = article.status === "draft";

  return (
    <Link
      href={`/articles/${encodeURIComponent(article.slug)}`}
      className="group block bg-white border border-[#d0d0d0] rounded-lg overflow-hidden hover:border-[#1f7a1f] hover:shadow-md transition"
    >
      {article.thumbnail_url ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={article.thumbnail_url}
          alt={article.title}
          className="w-full aspect-[16/9] object-cover bg-[#f5f5f5]"
          loading="lazy"
        />
      ) : (
        <div className="w-full aspect-[16/9] bg-gradient-to-br from-[#163016] to-[#1f7a1f] flex items-center justify-center">
          <span className="text-3xl">🐎</span>
        </div>
      )}
      <div className="p-3">
        <div className="flex items-center gap-2 mb-1.5">
          {isDraft && (
            <span className="text-[9px] font-bold text-[#F57C00] bg-[#fff3e0] px-1.5 py-0.5 rounded">
              下書き
            </span>
          )}
          <span className="text-[10px] text-[#999]">
            {formatDate(article.created_at)}
          </span>
        </div>
        <h3 className="text-sm font-bold text-[#222] leading-snug line-clamp-2 group-hover:text-[#1f7a1f] transition">
          {article.title}
        </h3>
        {article.description && (
          <p className="mt-1.5 text-[11px] text-[#666] leading-relaxed line-clamp-2">
            {article.description}
          </p>
        )}
        {article.author && (
          <div className="mt-2 text-[10px] text-[#999]">{article.author}</div>
        )}
      </div>
    </Link>
  );
}
