"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CHAT_API_BASE,
  CHAT_STAMPS,
  ChatMessage,
  fetchChatMessages,
  fetchChatOnline,
  sendChatMessage,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Channel = "global" | "jra" | "nar";

const CHANNEL_LABELS: Record<Channel, string> = {
  global: "全体",
  jra: "JRA今日",
  nar: "地方今日",
};

interface Props {
  defaultChannel?: Channel;
  embedded?: boolean;
  onClose?: () => void;
}

function formatRelativeTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const min = Math.floor(diff / 60_000);
    if (min < 1) return "たった今";
    if (min < 60) return `${min}分前`;
    return `${Math.floor(min / 60)}時間前`;
  } catch {
    return "";
  }
}

export default function ChatWidget({
  defaultChannel = "global",
  embedded = false,
  onClose,
}: Props) {
  const { authenticated } = useAuth();
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
  const wasInvisibleRef = useRef(false);
  channelRef.current = channel;

  const scrollToBottom = useCallback((smooth = true) => {
    endRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }, []);

  const connectSSE = useCallback(
    (ch: Channel) => {
      sseRef.current?.close();
      sseRef.current = null;

      const sse = new EventSource(`${CHAT_API_BASE}/api/chat/stream?channel=${ch}`);
      sseRef.current = sse;

      sse.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "connected") return;
          if (data.channel !== channelRef.current) return;
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.id)) return prev;
            const next = [...prev, data];
            return next.length > 50 ? next.slice(-50) : next;
          });
          setTimeout(() => scrollToBottom(true), 50);
        } catch { /* ignore */ }
      };

      sse.onerror = () => {
        sse.close();
        sseRef.current = null;
        setTimeout(() => {
          if (channelRef.current === ch) connectSSE(ch);
        }, 5_000);
      };
    },
    [scrollToBottom],
  );

  // Load messages and start SSE when channel changes
  useEffect(() => {
    setLoading(true);
    setMessages([]);

    fetchChatMessages(channel).then((msgs) => {
      setMessages(msgs);
      setLoading(false);
      setTimeout(() => scrollToBottom(false), 50);
    });

    connectSSE(channel);

    return () => {
      sseRef.current?.close();
      sseRef.current = null;
    };
  }, [channel, connectSSE, scrollToBottom]);

  // Online count — poll every 30 s
  useEffect(() => {
    const poll = () => fetchChatOnline().then(setOnline);
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  // Disconnect SSE when tab is hidden, reconnect when visible
  useEffect(() => {
    const handle = () => {
      if (document.visibilityState === "hidden") {
        sseRef.current?.close();
        sseRef.current = null;
      } else {
        connectSSE(channelRef.current);
      }
    };
    document.addEventListener("visibilitychange", handle);
    return () => document.removeEventListener("visibilitychange", handle);
  }, [connectSSE]);

  // Disconnect SSE when widget scrolls out of view (IntersectionObserver)
  useEffect(() => {
    const el = widgetRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) {
          wasInvisibleRef.current = true;
          sseRef.current?.close();
          sseRef.current = null;
        } else if (wasInvisibleRef.current) {
          wasInvisibleRef.current = false;
          connectSSE(channelRef.current);
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [connectSSE]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    setInput("");
    const res = await sendChatMessage(channel, text, null);
    if (!res.success) {
      setError(res.error || "送信に失敗しました");
      setInput(text);
    }
    setSending(false);
  };

  const handleStamp = async (stamp: string) => {
    if (!authenticated || sending) return;
    setSending(true);
    setError(null);
    const res = await sendChatMessage(channel, null, stamp);
    if (!res.success) setError(res.error || "送信に失敗しました");
    setSending(false);
  };

  // Stamp resonance: last 3 messages all same stamp
  const last3 = messages.slice(-3);
  const resonanceStamp =
    last3.length >= 3 && last3.every((m) => m.stamp && m.stamp === last3[0].stamp)
      ? last3[0].stamp
      : null;

  const containerH = embedded ? "h-[480px]" : "h-full";

  return (
    <div ref={widgetRef} className={`flex flex-col ${containerH} bg-white overflow-hidden`}>
      {/* Header */}
      <div className="bg-[#163016] text-white px-3 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold">💬 みんなのチャット</span>
          {(online[channel] ?? 0) > 0 && (
            <span className="text-[10px] bg-[#4ade80] text-[#163016] px-1.5 py-0.5 rounded-full font-black">
              {online[channel]}人
            </span>
          )}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="閉じる"
            className="text-[#a3c9a3] hover:text-white text-xl leading-none px-1"
          >
            ×
          </button>
        )}
      </div>

      {/* Channel tabs */}
      <div className="flex border-b border-[#e5e7eb] bg-[#f9fafb] shrink-0">
        {(Object.keys(CHANNEL_LABELS) as Channel[]).map((ch) => {
          const count = online[ch] ?? 0;
          const active = ch === channel;
          return (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className={`flex-1 py-2 text-[11px] font-bold transition-colors flex items-center justify-center gap-1 ${
                active
                  ? "text-[#163016] border-b-2 border-[#163016] bg-white -mb-px"
                  : "text-[#888] hover:text-[#444]"
              }`}
            >
              {CHANNEL_LABELS[ch]}
              {count > 0 && (
                <span
                  className={`text-[9px] px-1 py-0.5 rounded-full font-black ${
                    active ? "bg-[#163016] text-white" : "bg-[#ddd] text-[#555]"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-full text-[#aaa] text-xs">
            読み込み中...
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#bbb] text-xs gap-1.5">
            <span className="text-3xl">🏇</span>
            <span>まだメッセージがありません</span>
            <span>最初に話しかけてみましょう！</span>
          </div>
        ) : (
          <div className="space-y-2.5">
            {messages.map((msg, i) => (
              <div key={msg.id || i} className="flex gap-2 items-start">
                <div className="shrink-0 w-7 h-7 rounded-full bg-[#e8f5e9] flex items-center justify-center text-base">
                  {msg.avatar_emoji}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-[11px] font-bold text-[#333] truncate max-w-[120px]">
                      {msg.nickname}
                    </span>
                    <span className="text-[10px] text-[#bbb] shrink-0">
                      {formatRelativeTime(msg.created_at)}
                    </span>
                  </div>
                  {msg.stamp ? (
                    <div className="text-2xl mt-0.5 leading-none">{msg.stamp}</div>
                  ) : (
                    <div className="text-[13px] text-[#222] leading-relaxed break-words mt-0.5">
                      {msg.content}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Stamp resonance */}
            {resonanceStamp && (
              <div className="flex justify-center py-2">
                <span
                  className="text-6xl animate-bounce"
                  title="みんな同じスタンプ！"
                >
                  {resonanceStamp}
                </span>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-1.5 bg-red-50 text-red-600 text-[11px] border-t border-red-200 flex items-center justify-between shrink-0">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="underline ml-2 shrink-0">
            閉じる
          </button>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-[#e5e7eb] px-3 pt-2 pb-3 shrink-0 bg-[#fafafa]">
        {/* Stamps */}
        <div className="flex gap-3 mb-2">
          {CHAT_STAMPS.map((s) => (
            <button
              key={s}
              onClick={() => handleStamp(s)}
              disabled={!authenticated || sending}
              title={!authenticated ? "LINEログインして参加" : s}
              className={`text-xl leading-none transition-transform ${
                authenticated && !sending
                  ? "hover:scale-125 active:scale-90"
                  : "opacity-30 cursor-not-allowed"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Text input or login prompt */}
        {authenticated ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              maxLength={100}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="メッセージを入力… (100文字)"
              disabled={sending}
              className="flex-1 text-sm border border-[#ddd] rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#163016] bg-white min-w-0"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-3 py-1.5 bg-[#163016] text-white text-xs font-bold rounded-lg disabled:opacity-40 hover:bg-[#1f4a1f] transition-colors shrink-0"
            >
              送信
            </button>
          </div>
        ) : (
          <a
            href="/login"
            className="block text-center py-2 text-xs text-[#163016] font-bold border border-[#163016] rounded-lg hover:bg-[#163016] hover:text-white transition-colors"
          >
            🏇 LINEログインして参加する
          </a>
        )}
      </div>
    </div>
  );
}
