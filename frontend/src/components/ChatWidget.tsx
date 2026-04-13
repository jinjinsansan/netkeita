"use client";

import { useCallback, useEffect, useMemo, useRef, startTransition, useState } from "react";

const PENDING_PREFIX = "pending-";
import {
  CHAT_API_BASE,
  CHAT_STAMPS,
  ChatMessage,
  ReplyTo,
  deleteChatMessage,
  fetchChatMessages,
  sendChatMessage,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Channel = "global" | "jra" | "nar";

const STAMP_LABELS: Record<string, string> = {
  "🔥": "熱い",
  "💰": "儲かれ",
  "😭": "残念",
  "🏇": "GO!",
  "👍": "いいね",
};

const CHANNEL_LABELS: Record<Channel, string> = {
  global: "全体",
  jra: "中央競馬",
  nar: "地方競馬",
};

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

interface ContextMenuState {
  msg: ChatMessage;
  canDelete: boolean;
  confirmDelete: boolean;
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
  const isIOS = useMemo(() => {
    if (typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    return /iP(ad|hone|od)/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }, []);
  const [channel, setChannel] = useState<Channel>(defaultChannel);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [newCount, setNewCount] = useState(0);
  const [replyTo, setReplyTo] = useState<ReplyTo | null>(null);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [, setTick] = useState(0);

  const endRef = useRef<HTMLDivElement>(null);
  const scrollBoxRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sseRef = useRef<EventSource | null>(null);
  const scrollRafRef = useRef<number | null>(null);
  const channelRef = useRef<Channel>(channel);
  const wasHiddenRef = useRef(false);
  const isAtBottomRef = useRef(true);
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const touchStartPos = useRef<{ x: number; y: number } | null>(null);
  channelRef.current = channel;

  const mentionUsers = useMemo(() => {
    const seen = new Set<string>();
    const list: string[] = [];
    for (let i = messages.length - 1; i >= 0; i--) {
      const n = messages[i].nickname;
      if (!seen.has(n)) { seen.add(n); list.push(n); }
      if (list.length >= 8) break;
    }
    return list;
  }, [messages]);

  const filteredMentions = mentionQuery !== null
    ? mentionUsers.filter(n => n.toLowerCase().startsWith(mentionQuery.toLowerCase()))
    : [];

  const renderContent = (text: string, isMine: boolean) => {
    const parts = text.split(/(@\S+)/g);
    return parts.map((part, i) =>
      part.startsWith("@")
        ? <span key={i} className={`font-bold ${isMine ? "text-[#86efac]" : "text-[#163016]"}`}>{part}</span>
        : <span key={i}>{part}</span>
    );
  };

  const scrollBottom = useCallback((smooth = true) => {
    const el = scrollBoxRef.current;
    if (!el) return;
    const behavior: ScrollBehavior = smooth && !isIOS ? "smooth" : "auto";
    el.scrollTo({ top: el.scrollHeight, behavior });
    setIsAtBottom(true);
    isAtBottomRef.current = true;
    setNewCount(0);
  }, [isIOS]);

  const scheduleScrollBottom = useCallback((smooth = true) => {
    if (scrollRafRef.current) cancelAnimationFrame(scrollRafRef.current);
    scrollRafRef.current = requestAnimationFrame(() => {
      scrollRafRef.current = null;
      scrollBottom(smooth);
    });
  }, [scrollBottom]);

  const handleScroll = useCallback(() => {
    const el = scrollBoxRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setIsAtBottom(atBottom);
    isAtBottomRef.current = atBottom;
    if (atBottom) setNewCount(0);
  }, []);

  const connectSSE = useCallback(function connect(ch: Channel) {
    sseRef.current?.close();
    sseRef.current = null;
    const sse = new EventSource(`${CHAT_API_BASE}/api/chat/stream?channel=${ch}`);
    sseRef.current = sse;
    sse.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "connected") return;
        if (d.type === "message_deleted") {
          startTransition(() => setMessages((prev) => prev.filter((m) => m.id !== d.id)));
          return;
        }
        if (d.channel !== channelRef.current) return;
        startTransition(() => {
          setMessages((prev) => {
            if (prev.some((m) => m.id === d.id)) return prev;
            // Replace a matching optimistic (pending) message if present
            const pendingIdx = prev.findIndex(
              (m) => m.id.startsWith(PENDING_PREFIX) &&
                m.author_token === d.author_token &&
                m.content === d.content &&
                m.stamp === d.stamp,
            );
            if (pendingIdx !== -1) {
              const next = [...prev];
              next[pendingIdx] = d;
              return next;
            }
            const next = [...prev, d];
            return next.length > 50 ? next.slice(-50) : next;
          });
          if (!isAtBottomRef.current) setNewCount((n) => n + 1);
        });
        if (isAtBottomRef.current) scheduleScrollBottom(true);
      } catch { /* ignore */ }
    };
    sse.onerror = () => {
      sse.close(); sseRef.current = null;
      setTimeout(() => { if (channelRef.current === ch) connect(ch); }, 5_000);
    };
  }, [scheduleScrollBottom]);

  useEffect(() => {
    setLoading(true); setMessages([]); setNewCount(0); setIsAtBottom(true);
    setReplyTo(null); setMentionQuery(null); setContextMenu(null);
    isAtBottomRef.current = true;
    fetchChatMessages(channel).then((msgs) => {
      setMessages(msgs); setLoading(false);
      scheduleScrollBottom(false);
    });
    connectSSE(channel);
    return () => { sseRef.current?.close(); sseRef.current = null; };
  }, [channel, connectSSE, scheduleScrollBottom]);

  useEffect(() => {
    const h = () => {
      if (document.visibilityState === "hidden") { sseRef.current?.close(); sseRef.current = null; }
      else connectSSE(channelRef.current);
    };
    document.addEventListener("visibilitychange", h);
    return () => document.removeEventListener("visibilitychange", h);
  }, [connectSSE]);

  // Refresh relative timestamps every 60 seconds
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (embedded) return;
    const el = widgetRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) { wasHiddenRef.current = true; sseRef.current?.close(); sseRef.current = null; }
      else if (wasHiddenRef.current) { wasHiddenRef.current = false; connectSSE(channelRef.current); }
    }, { threshold: 0 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [connectSSE, embedded]);

  useEffect(() => {
    return () => {
      if (scrollRafRef.current) cancelAnimationFrame(scrollRafRef.current);
    };
  }, []);

  const makeOptimistic = useCallback((content: string | null, stamp: string | null): ChatMessage => ({
    id: `${PENDING_PREFIX}${Date.now()}`,
    channel,
    nickname: user?.display_name ?? "あなた",
    avatar_url: user?.picture_url ?? null,
    author_token: myToken ?? "",
    content,
    stamp,
    reply_to: replyTo,
    created_at: new Date().toISOString(),
    pending: true,
  } as ChatMessage & { pending: boolean }), [channel, user, myToken, replyTo]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    const optimistic = makeOptimistic(text, null);
    setSending(true); setError(null); setInput(""); setMentionQuery(null);
    startTransition(() => {
      setMessages((prev) => {
        const next = [...prev, optimistic];
        return next.length > 50 ? next.slice(-50) : next;
      });
    });
    if (isAtBottomRef.current) scheduleScrollBottom(true);
    const res = await sendChatMessage(channel, text, null, replyTo);
    if (!res.success) {
      setError(res.error || "送信に失敗しました");
      setInput(text);
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } else {
      setReplyTo(null);
    }
    setSending(false);
  };

  const handleDelete = async (msg: ChatMessage) => {
    setContextMenu(null);
    setMessages((prev) => prev.filter((m) => m.id !== msg.id));
    await deleteChatMessage(msg.id, msg.channel);
  };

  const handleStamp = async (stamp: string) => {
    if (!authenticated || sending) return;
    const optimistic = makeOptimistic(null, stamp);
    setSending(true); setError(null);
    startTransition(() => {
      setMessages((prev) => {
        const next = [...prev, optimistic];
        return next.length > 50 ? next.slice(-50) : next;
      });
    });
    if (isAtBottomRef.current) scheduleScrollBottom(true);
    const res = await sendChatMessage(channel, null, stamp, replyTo);
    if (!res.success) {
      setError(res.error || "送信に失敗しました");
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } else {
      setReplyTo(null);
    }
    setSending(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(val);
    const match = val.match(/@([^\s]*)$/);
    setMentionQuery(match ? match[1] : null);
  };

  const selectMention = (nickname: string) => {
    setInput(prev => prev.replace(/@[^\s]*$/, `@${nickname} `));
    setMentionQuery(null);
    inputRef.current?.focus();
  };

  // ── Long-press / context menu ──────────────────────────────────────────────

  const openContextMenu = useCallback((msg: ChatMessage) => {
    const canDelete = isAdmin || (!!myToken && msg.author_token === myToken);
    if (typeof navigator !== "undefined" && "vibrate" in navigator) {
      try { navigator.vibrate(50); } catch { /* ignore */ }
    }
    setContextMenu({ msg, canDelete, confirmDelete: false });
  }, [isAdmin, myToken]);

  const handleTouchStart = useCallback((msg: ChatMessage, e: React.TouchEvent) => {
    const touch = e.touches[0];
    touchStartPos.current = { x: touch.clientX, y: touch.clientY };
    longPressTimer.current = setTimeout(() => openContextMenu(msg), 500);
  }, [openContextMenu]);

  const handleTouchEnd = useCallback(() => {
    if (longPressTimer.current) { clearTimeout(longPressTimer.current); longPressTimer.current = null; }
    touchStartPos.current = null;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartPos.current || !longPressTimer.current) return;
    const touch = e.touches[0];
    const dx = Math.abs(touch.clientX - touchStartPos.current.x);
    const dy = Math.abs(touch.clientY - touchStartPos.current.y);
    if (dx > 12 || dy > 12) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  const handleContextMenu = useCallback((msg: ChatMessage, e: React.MouseEvent) => {
    e.preventDefault();
    openContextMenu(msg);
  }, [openContextMenu]);

  // ───────────────────────────────────────────────────────────────────────────

  const last3 = messages.slice(-3);
  const resonance = last3.length >= 3 && last3.every((m) => m.stamp && m.stamp === last3[0].stamp)
    ? last3[0].stamp : null;

  const charCount = input.length;
  const charWarning = charCount > 80;

  return (
    <div
      ref={widgetRef}
      className={`relative flex flex-col ${embedded ? "h-[480px]" : "h-full"} bg-white overflow-hidden`}
    >

      {/* ── Context menu (bottom sheet) ───────────────────────────────── */}
      {contextMenu && (
        <div
          className="absolute inset-0 z-50 flex flex-col justify-end"
          style={{ background: "rgba(0,0,0,0.5)" }}
          onClick={() => setContextMenu(null)}
        >
          <div
            className="bg-white rounded-t-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Message preview */}
            <div className="px-5 py-3.5 bg-[#f7f7f7] border-b border-[#ebebeb]">
              <p className="text-[11px] font-bold text-[#999] mb-0.5">{contextMenu.msg.nickname}</p>
              <p className="text-sm text-[#555] line-clamp-2">
                {contextMenu.msg.content || contextMenu.msg.stamp || ""}
              </p>
            </div>

            {!contextMenu.confirmDelete ? (
              <>
                {/* Reply */}
                {authenticated && (
                  <button
                    className="w-full flex items-center gap-4 px-5 py-4 active:bg-[#f0f0f0] transition-colors text-left"
                    onClick={() => {
                      setReplyTo({
                        id: contextMenu.msg.id,
                        nickname: contextMenu.msg.nickname,
                        content: contextMenu.msg.content || contextMenu.msg.stamp,
                      });
                      setContextMenu(null);
                      setTimeout(() => inputRef.current?.focus(), 150);
                    }}
                  >
                    <span className="w-9 h-9 rounded-full bg-[#e8f5e9] flex items-center justify-center text-lg shrink-0">↩</span>
                    <span className="text-[15px] font-semibold text-[#222]">返信</span>
                  </button>
                )}

                {/* Delete */}
                {contextMenu.canDelete && (
                  <button
                    className="w-full flex items-center gap-4 px-5 py-4 active:bg-red-50 transition-colors text-left border-t border-[#f0f0f0]"
                    onClick={() => setContextMenu(prev => prev ? { ...prev, confirmDelete: true } : null)}
                  >
                    <span className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center text-lg shrink-0">🗑</span>
                    <span className="text-[15px] font-semibold text-red-500">削除</span>
                  </button>
                )}
              </>
            ) : (
              /* Delete confirmation */
              <div>
                <p className="text-center text-[13px] text-[#555] py-4 px-6">
                  このメッセージを削除しますか？<br />
                  <span className="text-[11px] text-[#999]">削除後は元に戻せません</span>
                </p>
                <div className="flex border-t border-[#ebebeb]">
                  <button
                    className="flex-1 py-4 text-[15px] font-semibold text-[#999] active:bg-[#f5f5f5] transition-colors border-r border-[#ebebeb]"
                    onClick={() => setContextMenu(null)}
                  >
                    キャンセル
                  </button>
                  <button
                    className="flex-1 py-4 text-[15px] font-bold text-red-500 active:bg-red-50 transition-colors"
                    onClick={() => handleDelete(contextMenu.msg)}
                  >
                    削除する
                  </button>
                </div>
              </div>
            )}

            {/* Cancel row (iOS action sheet style) */}
            <div className="border-t-[6px] border-[#f0f0f0]">
              <button
                className="w-full py-4 text-[15px] font-bold text-[#333] active:bg-[#f5f5f5] transition-colors"
                onClick={() => setContextMenu(null)}
              >
                キャンセル
              </button>
            </div>
            {/* Safe area bottom padding */}
            <div style={{ height: "env(safe-area-inset-bottom)" }} />
          </div>
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────────── */}
      <div className="bg-[#163016] px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[#4ade80] shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
          </svg>
          <span className="text-white font-bold text-sm">みんなのチャット</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full text-white/50 hover:text-white hover:bg-white/10 active:bg-white/20 transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* ── Channel tabs ──────────────────────────────────────────────── */}
      <div className="flex bg-white border-b border-[#f0f0f0] shrink-0">
        {(Object.keys(CHANNEL_LABELS) as Channel[]).map((ch) => {
          const active = ch === channel;
          return (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className={`flex-1 py-2.5 text-[11px] font-bold relative transition-colors
                ${active ? "text-[#163016]" : "text-[#bbb] hover:text-[#777]"}`}
            >
              {CHANNEL_LABELS[ch]}
              {active && (
                <span className="absolute bottom-0 left-6 right-6 h-[2px] bg-[#163016] rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Scroll-to-bottom button ───────────────────────────────────── */}
      {!isAtBottom && (
        <div className="relative h-0 overflow-visible z-10 shrink-0">
          <button
            onClick={() => scrollBottom(true)}
            className="absolute left-1/2 -translate-x-1/2 -top-4 flex items-center gap-1.5 bg-[#163016] text-white text-[11px] font-bold px-3 py-1.5 rounded-full shadow-lg hover:bg-[#1f4a1f] active:scale-95 transition-all"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
              <path d="M7 10l5 5 5-5z"/>
            </svg>
            {newCount > 0 ? `${newCount}件の新着` : "最新へ"}
          </button>
        </div>
      )}

      {/* ── Messages ──────────────────────────────────────────────────── */}
      <div
        ref={scrollBoxRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-3 min-h-0 bg-[#f2f3f5]"
        style={{ WebkitOverflowScrolling: "touch", overscrollBehavior: "contain" }}
      >
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
          <div className="space-y-1.5">
            {messages.map((msg) => {
              const isMine = !!myToken && msg.author_token === myToken;
              const isPending = msg.id.startsWith(PENDING_PREFIX);
              const s = avatarStyle(msg.nickname);
              return (
                <div
                  key={msg.id}
                  className={`flex items-end gap-2 transition-opacity ${isMine ? "flex-row-reverse" : "flex-row"} ${isPending ? "opacity-60" : "opacity-100"}`}
                  onTouchStart={(e) => { if (!isPending) handleTouchStart(msg, e); }}
                  onTouchEnd={handleTouchEnd}
                  onTouchMove={handleTouchMove}
                  onContextMenu={(e) => { if (!isPending) handleContextMenu(msg, e); }}
                >
                  {/* Avatar — others only */}
                  {!isMine && (
                    <div className="shrink-0 mb-1">
                      {msg.avatar_url ? (
                        <img src={msg.avatar_url} alt={msg.nickname} className="w-9 h-9 rounded-full object-cover" />
                      ) : (
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-[13px] font-black select-none"
                          style={{ backgroundColor: s.bg, color: s.fg }}
                        >
                          {initial(msg.nickname)}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Bubble area */}
                  <div className={`flex flex-col max-w-[72%] ${isMine ? "items-end" : "items-start"}`}>
                    {/* Nickname (others only) */}
                    {!isMine && (
                      <span className="text-[11px] font-bold text-[#555] mb-0.5 ml-1 truncate max-w-[140px]">
                        {msg.nickname}
                      </span>
                    )}

                    {/* Reply quote */}
                    {msg.reply_to && (
                      <div className={`flex items-start gap-1.5 mb-1 px-2.5 py-1.5 rounded-xl max-w-full
                        ${isMine
                          ? "bg-[#0f2a0f]/20 border border-[#163016]/20"
                          : "bg-white/90 border border-[#e0e0e0]"
                        }`}
                      >
                        <span className="text-[11px] font-bold text-[#163016]/80 shrink-0">@{msg.reply_to.nickname}</span>
                        <span className="text-[11px] text-[#888] truncate">{msg.reply_to.content || "スタンプ"}</span>
                      </div>
                    )}

                    {/* Bubble */}
                    {msg.stamp ? (
                      <span className="text-3xl leading-none py-1 select-none">{msg.stamp}</span>
                    ) : (
                      <div
                        className={`px-3.5 py-2.5 text-[14px] leading-relaxed break-words select-text
                          ${isMine
                            ? "bg-[#163016] text-white rounded-2xl rounded-br-md"
                            : "bg-white text-[#222] rounded-2xl rounded-bl-md shadow-sm"
                          }`}
                        style={{ wordBreak: "break-word" }}
                      >
                        {msg.content ? renderContent(msg.content, isMine) : null}
                      </div>
                    )}

                    {/* Timestamp */}
                    <span className={`text-[11px] mt-0.5 ${isMine ? "mr-1" : "ml-1"} ${isPending ? "text-[#bbb] italic" : "text-[#aaa]"}`}>
                      {isPending ? "送信中…" : relTime(msg.created_at)}
                    </span>
                  </div>
                </div>
              );
            })}

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

      {/* ── Error ─────────────────────────────────────────────────────── */}
      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-500 text-[11px] border-t border-red-100 flex items-center justify-between shrink-0">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-2 w-8 h-8 flex items-center justify-center rounded-full hover:bg-red-100 active:bg-red-200 transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Reply preview bar ─────────────────────────────────────────── */}
      {replyTo && (
        <div className="flex items-center gap-2 px-3 py-2.5 bg-[#f0f7f0] border-t border-[#c8e6c9] shrink-0">
          <div className="w-0.5 self-stretch bg-[#163016] rounded-full shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-bold text-[#163016]">↩ @{replyTo.nickname} に返信</p>
            <p className="text-[11px] text-[#666] truncate">{replyTo.content || "スタンプ"}</p>
          </div>
          <button
            onClick={() => setReplyTo(null)}
            className="w-9 h-9 flex items-center justify-center rounded-full text-[#888] hover:text-[#333] hover:bg-black/5 active:bg-black/10 active:text-[#333] transition-colors shrink-0"
            aria-label="返信をキャンセル"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Input area ────────────────────────────────────────────────── */}
      <div
        className="border-t border-[#e8e8e8] bg-white px-3 pt-2.5 shrink-0 relative"
        style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}
      >
        {/* @mention dropdown */}
        {mentionQuery !== null && filteredMentions.length > 0 && (
          <div className="absolute bottom-full left-3 right-3 mb-1 bg-white border border-[#e0e0e0] rounded-xl shadow-lg overflow-hidden z-20">
            {filteredMentions.map((n) => {
              const ms = avatarStyle(n);
              return (
                <button
                  key={n}
                  onMouseDown={(e) => { e.preventDefault(); selectMention(n); }}
                  className="w-full flex items-center gap-2.5 px-3 py-3 hover:bg-[#f5f5f5] active:bg-[#eeeeee] transition-colors text-left"
                >
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-black shrink-0"
                    style={{ backgroundColor: ms.bg, color: ms.fg }}
                  >
                    {initial(n)}
                  </div>
                  <span className="text-sm font-bold text-[#333]">@{n}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Stamp row */}
        <div className="flex gap-1.5 mb-2.5 overflow-x-auto pb-0.5 scrollbar-none">
          {CHAT_STAMPS.map((s) => (
            <button
              key={s}
              onClick={() => handleStamp(s)}
              disabled={!authenticated || sending}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-full shrink-0 select-none transition-all
                ${authenticated && !sending
                  ? "bg-[#f0f0f0] hover:bg-[#e4e4e4] active:scale-95 active:bg-[#d8d8d8]"
                  : "bg-[#f5f5f5] opacity-30 cursor-not-allowed"}`}
            >
              <span className="text-sm leading-none">{s}</span>
              <span className="text-[10px] font-bold text-[#555] leading-none">{STAMP_LABELS[s]}</span>
            </button>
          ))}
        </div>

        {/* Text input row */}
        {authenticated ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 relative min-w-0">
              <input
                ref={inputRef}
                type="text"
                value={input}
                maxLength={100}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                  if (e.key === "Escape") { setMentionQuery(null); setReplyTo(null); return; }
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
                }}
                placeholder={replyTo ? `@${replyTo.nickname} に返信…` : "メッセージを入力…"}
                disabled={sending}
                className="w-full bg-[#f5f5f5] rounded-full px-4 py-2.5 focus:outline-none focus:bg-[#ededee] transition-colors placeholder-[#bbb]"
                style={{ fontSize: "16px" }}
              />
              {charWarning && (
                <span className={`absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold pointer-events-none
                  ${charCount >= 100 ? "text-red-500" : "text-orange-400"}`}
                >
                  {100 - charCount}
                </span>
              )}
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="w-10 h-10 rounded-full bg-[#163016] flex items-center justify-center disabled:opacity-25 hover:bg-[#1f4a1f] active:scale-90 transition-all shrink-0"
            >
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        ) : (
          <a
            href="/login"
            className="flex items-center justify-center gap-2 py-3 rounded-full bg-[#163016] text-white text-sm font-bold hover:bg-[#1f4a1f] active:bg-[#0f2a0f] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/>
            </svg>
            LINEでログインして参加する
          </a>
        )}
      </div>
    </div>
  );
}
