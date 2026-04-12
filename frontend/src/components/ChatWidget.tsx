"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CHAT_API_BASE,
  CHAT_STAMPS,
  ChatMessage,
  deleteChatMessage,
  fetchChatMessages,
  fetchChatOnline,
  sendChatMessage,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Channel = "global" | "jra" | "nar";

const CHANNEL_LABELS: Record<Channel, string> = {
  global: "全体",
  jra: "中央競馬",
  nar: "地方競馬",
};

// Deterministic avatar color from name
const PALETTE = [
  { bg: "#fecdd3", fg: "#9f1239" },
  { bg: "#fed7aa", fg: "#9a3412" },
  { bg: "#fef08a", fg: "#713f12" },
  { bg: "#bbf7d0", fg: "#14532d" },
  { bg: "#bae6fd", fg: "#0c4a6e" },
  { bg: "#c7d2fe", fg: "#312e81" },
  { bg: "#f5d0fe", fg: "#701a75" },
  { bg: "#fda4af", fg: "#881337" },
];

function avatarStyle(name: string) {
  let h = 0;
  for (const c of name) h = ((h * 31 + c.charCodeAt(0)) >>> 0);
  return PALETTE[h % PALETTE.length];
}

function initial(name: string) {
  return (name.trim().charAt(0) || "?").toUpperCase();
}

function relTime(iso: string) {
  try {
    const min = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
    if (min < 1) return "今";
    if (min < 60) return `${min}分前`;
    return `${Math.floor(min / 60)}時間前`;
  } catch { return ""; }
}

interface Props {
  defaultChannel?: Channel;
  embedded?: boolean;
  onClose?: () => void;
}

export default function ChatWidget({ defaultChannel = "global", embedded = false, onClose }: Props) {
  const { authenticated, user } = useAuth();
  const myToken = user?.author_token ?? null;
  const isAdmin = user?.is_admin ?? false;
  const [channel, setChannel] = useState<Channel>(defaultChannel);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [online, setOnline] = useState<Record<string, number>>({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const endRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);
  const channelRef = useRef<Channel>(channel);
  const wasHiddenRef = useRef(false);
  channelRef.current = channel;

  const scrollBottom = useCallback((smooth = true) => {
    endRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }, []);

  const connectSSE = useCallback((ch: Channel) => {
    sseRef.current?.close();
    sseRef.current = null;
    const sse = new EventSource(`${CHAT_API_BASE}/api/chat/stream?channel=${ch}`);
    sseRef.current = sse;
    sse.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "connected") return;
        if (d.type === "message_deleted") {
          setMessages((prev) => prev.filter((m) => m.id !== d.id));
          return;
        }
        if (d.channel !== channelRef.current) return;
        setMessages((prev) => {
          if (prev.some((m) => m.id === d.id)) return prev;
          const next = [...prev, d];
          return next.length > 50 ? next.slice(-50) : next;
        });
        setTimeout(() => scrollBottom(true), 50);
      } catch { /* ignore */ }
    };
    sse.onerror = () => {
      sse.close(); sseRef.current = null;
      setTimeout(() => { if (channelRef.current === ch) connectSSE(ch); }, 5_000);
    };
  }, [scrollBottom]);

  useEffect(() => {
    setLoading(true); setMessages([]);
    fetchChatMessages(channel).then((msgs) => {
      setMessages(msgs); setLoading(false);
      setTimeout(() => scrollBottom(false), 50);
    });
    connectSSE(channel);
    return () => { sseRef.current?.close(); sseRef.current = null; };
  }, [channel, connectSSE, scrollBottom]);

  useEffect(() => {
    const poll = () => fetchChatOnline().then(setOnline);
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const h = () => {
      if (document.visibilityState === "hidden") { sseRef.current?.close(); sseRef.current = null; }
      else connectSSE(channelRef.current);
    };
    document.addEventListener("visibilitychange", h);
    return () => document.removeEventListener("visibilitychange", h);
  }, [connectSSE]);

  useEffect(() => {
    const el = widgetRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) { wasHiddenRef.current = true; sseRef.current?.close(); sseRef.current = null; }
      else if (wasHiddenRef.current) { wasHiddenRef.current = false; connectSSE(channelRef.current); }
    }, { threshold: 0.1 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [connectSSE]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true); setError(null); setInput("");
    const res = await sendChatMessage(channel, text, null);
    if (!res.success) { setError(res.error || "送信に失敗しました"); setInput(text); }
    setSending(false);
  };

  const handleDelete = async (msg: ChatMessage) => {
    setMessages((prev) => prev.filter((m) => m.id !== msg.id));
    await deleteChatMessage(msg.id, msg.channel);
  };

  const handleStamp = async (stamp: string) => {
    if (!authenticated || sending) return;
    setSending(true); setError(null);
    const res = await sendChatMessage(channel, null, stamp);
    if (!res.success) setError(res.error || "送信に失敗しました");
    setSending(false);
  };

  const last3 = messages.slice(-3);
  const resonance = last3.length >= 3 && last3.every((m) => m.stamp && m.stamp === last3[0].stamp)
    ? last3[0].stamp : null;

  return (
    <div ref={widgetRef} className={`flex flex-col ${embedded ? "h-[480px]" : "h-full"} bg-white overflow-hidden`}>

      {/* ── Header ──────────────────────────────────── */}
      <div className="bg-[#163016] px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[#4ade80] shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
          </svg>
          <span className="text-white font-bold text-sm">みんなのチャット</span>
        </div>
        <div className="flex items-center gap-2.5">
          {(online[channel] ?? 0) > 0 && (
            <div className="flex items-center gap-1.5 bg-white/10 rounded-full px-2.5 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] animate-pulse block shrink-0" />
              <span className="text-[#4ade80] text-[10px] font-bold">{online[channel]}人</span>
            </div>
          )}
          {onClose && (
            <button onClick={onClose} className="text-white/40 hover:text-white transition-colors text-base leading-none">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* ── Channel tabs ────────────────────────────── */}
      <div className="flex bg-white border-b border-[#f0f0f0] shrink-0">
        {(Object.keys(CHANNEL_LABELS) as Channel[]).map((ch) => {
          const cnt = online[ch] ?? 0;
          const active = ch === channel;
          return (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className={`flex-1 py-2.5 text-[11px] font-bold relative transition-colors
                ${active ? "text-[#163016]" : "text-[#bbb] hover:text-[#777]"}`}
            >
              {CHANNEL_LABELS[ch]}
              {cnt > 0 && (
                <span className={`ml-1 font-black text-[9px] ${active ? "text-[#4ade80]" : "text-[#ccc]"}`}>
                  {cnt}
                </span>
              )}
              {active && (
                <span className="absolute bottom-0 left-6 right-6 h-[2px] bg-[#163016] rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Messages ────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0 bg-[#f9fafb]">
        {loading ? (
          <div className="flex items-center justify-center h-full gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#ccc] animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center select-none">
            <div className="w-14 h-14 rounded-2xl bg-[#e8f5e9] flex items-center justify-center">
              <svg className="w-7 h-7 text-[#86efac]" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
              </svg>
            </div>
            <div>
              <p className="text-xs font-bold text-[#999]">まだ誰もいません</p>
              <p className="text-[11px] text-[#bbb] mt-0.5">最初の一言を投稿してみましょう</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg, i) => {
              const s = avatarStyle(msg.nickname);
              const canDelete = isAdmin || (!!myToken && msg.author_token === myToken);
              return (
                <div key={msg.id || i} className="flex gap-2.5 group">
                  {/* Avatar */}
                  <div className="shrink-0 mt-0.5">
                    {msg.avatar_url ? (
                      <img
                        src={msg.avatar_url}
                        alt={msg.nickname}
                        className="w-7 h-7 rounded-full object-cover"
                      />
                    ) : (
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-black select-none"
                        style={{ backgroundColor: s.bg, color: s.fg }}
                      >
                        {initial(msg.nickname)}
                      </div>
                    )}
                  </div>
                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-1.5 mb-0.5">
                      <span className="text-[11px] font-bold text-[#1a1a1a] truncate max-w-[120px]">
                        {msg.nickname}
                      </span>
                      <span className="text-[9px] text-[#ccc] shrink-0">{relTime(msg.created_at)}</span>
                    </div>
                    {msg.stamp ? (
                      <span className="text-2xl leading-none">{msg.stamp}</span>
                    ) : (
                      <p className="text-[13px] text-[#333] leading-relaxed break-words">{msg.content}</p>
                    )}
                  </div>
                  {/* Delete button — always visible on touch, hover-reveal on desktop */}
                  {canDelete && (
                    <button
                      onClick={() => handleDelete(msg)}
                      className="shrink-0 self-start mt-0.5 text-[#ccc] active:text-red-400 transition-colors text-[11px] leading-none px-1 opacity-0 group-hover:opacity-100 [@media(hover:none)]:opacity-100 hover:text-red-400"
                      title="削除"
                    >
                      ✕
                    </button>
                  )}
                </div>
              );
            })}

            {/* Stamp resonance */}
            {resonance && (
              <div className="flex justify-center py-2 pointer-events-none">
                <span
                  className="text-6xl animate-bounce select-none"
                  style={{ filter: "drop-shadow(0 4px 16px rgba(0,0,0,0.12))" }}
                >
                  {resonance}
                </span>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* ── Error ───────────────────────────────────── */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-500 text-[11px] border-t border-red-100 flex items-center justify-between shrink-0">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* ── Input ───────────────────────────────────── */}
      <div className="border-t border-[#f0f0f0] bg-white px-3 pt-2.5 pb-safe-3 shrink-0" style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}>
        {/* Stamp row */}
        <div className="flex gap-1.5 mb-2.5">
          {CHAT_STAMPS.map((s) => (
            <button
              key={s}
              onClick={() => handleStamp(s)}
              disabled={!authenticated || sending}
              className={`flex-1 py-1.5 rounded-xl text-lg transition-all select-none
                ${authenticated && !sending
                  ? "bg-[#f5f5f5] hover:bg-[#ebebeb] active:scale-90 active:bg-[#e0e0e0]"
                  : "opacity-20 cursor-not-allowed"}`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Text row */}
        {authenticated ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              maxLength={100}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="メッセージを入力…"
              disabled={sending}
              className="flex-1 text-base bg-[#f5f5f5] rounded-full px-4 py-2 focus:outline-none focus:bg-[#ededee] transition-colors min-w-0 placeholder-[#bbb]"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="w-9 h-9 rounded-full bg-[#163016] flex items-center justify-center disabled:opacity-25 hover:bg-[#1f4a1f] active:scale-90 transition-all shrink-0"
            >
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        ) : (
          <a
            href="/login"
            className="flex items-center justify-center gap-2 py-2.5 rounded-full bg-[#163016] text-white text-xs font-bold hover:bg-[#1f4a1f] transition-colors"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/>
            </svg>
            LINEでログインして参加する
          </a>
        )}
      </div>
    </div>
  );
}
