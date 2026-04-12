"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { fetchChatOnline } from "@/lib/api";

const ChatWidget = dynamic(() => import("./ChatWidget"), { ssr: false });

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [totalOnline, setTotalOnline] = useState(0);

  useEffect(() => {
    const poll = async () => {
      const online = await fetchChatOnline();
      setTotalOnline(Object.values(online).reduce((a, b) => a + b, 0));
    };
    poll();
    const id = setInterval(poll, 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open]);

  // Allow external triggers (e.g. top-page chat banner)
  useEffect(() => {
    const h = () => setOpen(true);
    window.addEventListener("open-floating-chat", h);
    return () => window.removeEventListener("open-floating-chat", h);
  }, []);

  return (
    <>
      {/* ── Floating button ─────────────────────────── */}
      <button
        onClick={() => setOpen(true)}
        aria-label="チャットを開く"
        className="fixed bottom-6 right-5 z-40 w-14 h-14 bg-[#163016] rounded-2xl shadow-xl flex items-center justify-center hover:bg-[#1a3e1a] hover:shadow-2xl hover:scale-105 active:scale-95 transition-all duration-150"
      >
        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
        </svg>

        {/* Online badge */}
        {totalOnline > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[20px] h-5 bg-[#4ade80] text-[#163016] text-[9px] font-black rounded-full flex items-center justify-center px-1.5 shadow-sm pointer-events-none select-none">
            {totalOnline}
          </span>
        )}
      </button>

      {/* ── Drawer ──────────────────────────────────── */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-end justify-end"
          onClick={(e) => e.target === e.currentTarget && setOpen(false)}
        >
          {/* Mobile backdrop */}
          <div
            className="absolute inset-0 bg-black/30 sm:hidden"
            style={{ backdropFilter: "blur(2px)" }}
            onClick={() => setOpen(false)}
          />
          {/* Panel */}
          <div className="relative w-full sm:w-[380px] h-[88dvh] sm:h-[620px] bg-white rounded-t-3xl sm:rounded-2xl sm:mb-6 sm:mr-5 shadow-2xl flex flex-col overflow-hidden">
            <ChatWidget onClose={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
