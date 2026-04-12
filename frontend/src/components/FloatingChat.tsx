"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { fetchChatOnline } from "@/lib/api";

const ChatWidget = dynamic(() => import("./ChatWidget"), { ssr: false });

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [totalOnline, setTotalOnline] = useState(0);

  // Lightweight polling for online count — no persistent SSE connection
  useEffect(() => {
    const poll = async () => {
      const online = await fetchChatOnline();
      const total = Object.values(online).reduce((a, b) => a + b, 0);
      setTotalOnline(total);
    };
    poll();
    const id = setInterval(poll, 60_000);
    return () => clearInterval(id);
  }, []);

  const handleOpen = () => setOpen(true);
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
        {totalOnline > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[20px] h-5 bg-[#4ade80] text-[#163016] text-[9px] font-black rounded-full flex items-center justify-center px-1">
            {totalOnline}
          </span>
        )}
      </button>

      {/* Backdrop + Drawer */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-end"
          onClick={(e) => e.target === e.currentTarget && handleClose()}
        >
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
