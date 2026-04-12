"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { CHAT_API_BASE } from "@/lib/api";

const ChatWidget = dynamic(() => import("./ChatWidget"), { ssr: false });

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const sseRef = useRef<EventSource | null>(null);
  const openRef = useRef(false);
  openRef.current = open;

  // Track new messages in background when chat is closed
  useEffect(() => {
    const connect = () => {
      sseRef.current?.close();
      const sse = new EventSource(`${CHAT_API_BASE}/api/chat/stream?channel=global`);
      sseRef.current = sse;
      sse.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "connected") return;
          if (!openRef.current) {
            setUnread((n) => Math.min(n + 1, 99));
          }
        } catch { /* ignore */ }
      };
      sse.onerror = () => {
        sse.close();
        sseRef.current = null;
        setTimeout(connect, 10_000);
      };
    };
    connect();
    return () => {
      sseRef.current?.close();
      sseRef.current = null;
    };
  }, []);

  const handleOpen = () => {
    setOpen(true);
    setUnread(0);
  };

  const handleClose = () => setOpen(false);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handle = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handle);
    return () => document.removeEventListener("keydown", handle);
  }, [open]);

  return (
    <>
      {/* Floating button */}
      <button
        onClick={handleOpen}
        aria-label="チャットを開く"
        className="fixed bottom-6 right-4 z-40 w-14 h-14 bg-[#163016] text-white rounded-full shadow-xl flex items-center justify-center text-2xl hover:bg-[#1f4a1f] transition-colors active:scale-95"
      >
        💬
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[9px] font-black rounded-full flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {/* Backdrop + Drawer */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-end justify-end"
          onClick={(e) => e.target === e.currentTarget && handleClose()}
        >
          {/* Semi-transparent backdrop for mobile */}
          <div
            className="absolute inset-0 bg-black/20 sm:hidden"
            onClick={handleClose}
          />
          <div className="relative w-full sm:w-[380px] h-[85dvh] sm:h-[600px] bg-white rounded-t-2xl sm:rounded-2xl sm:mb-6 sm:mr-4 shadow-2xl flex flex-col overflow-hidden">
            <ChatWidget onClose={handleClose} />
          </div>
        </div>
      )}
    </>
  );
}
