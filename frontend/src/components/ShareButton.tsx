"use client";

export default function ShareButton({
  title,
  url,
}: {
  title: string;
  url: string;
}) {
  const text = encodeURIComponent(title);
  const encodedUrl = encodeURIComponent(url);
  const webUrl = `https://x.com/intent/tweet?text=${text}&url=${encodedUrl}`;

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // スマートフォンではXアプリのディープリンクを試みる
    const ua = navigator.userAgent;
    const isMobile = /iPhone|iPad|iPod|Android/i.test(ua);
    if (!isMobile) return; // PCはそのままweb

    e.preventDefault();
    // twitter:// スキームでアプリ起動を試みる
    const appUrl = `twitter://post?message=${text}%20${encodedUrl}`;
    window.location.href = appUrl;

    // アプリが入っていない場合のフォールバック（300ms後にwebを開く）
    setTimeout(() => {
      window.open(webUrl, "_blank", "noopener,noreferrer");
    }, 300);
  };

  return (
    <a
      href={webUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
      aria-label="Xでシェア"
      className="inline-flex items-center gap-2 bg-black hover:bg-[#333] text-white text-xs font-bold px-4 py-2 rounded-lg transition"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
      Xでシェア
    </a>
  );
}
