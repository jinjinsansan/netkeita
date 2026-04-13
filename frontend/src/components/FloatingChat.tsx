"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

const ChatWidget = dynamic(() => import("./ChatWidget"), { ssr: false });

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const isIOS = useMemo(() => {
    if (typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    return /iP(ad|hone|od)/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }, []);

  // Lock body scroll when drawer is open to prevent background jitter
  useEffect(() => {
    if (open) {
      const body = document.body;
      const prev = {
        overflow: body.style.overflow,
        position: body.style.position,
        top: body.style.top,
        left: body.style.left,
        right: body.style.right,
        width: body.style.width,
        touchAction: body.style.touchAction,
      };
      const scrollY = window.scrollY;
      if (isIOS) {
        body.style.position = "fixed";
        body.style.top = `-${scrollY}px`;
        body.style.left = "0";
        body.style.right = "0";
        body.style.width = "100%";
        body.style.touchAction = "none";
      } else {
        body.style.overflow = "hidden";
      }
      return () => {
        body.style.overflow = prev.overflow;
        body.style.position = prev.position;
        body.style.top = prev.top;
        body.style.left = prev.left;
        body.style.right = prev.right;
        body.style.width = prev.width;
        body.style.touchAction = prev.touchAction;
        if (isIOS) window.scrollTo(0, scrollY);
      };
    }
  }, [open, isIOS]);

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
        style={{ willChange: "transform", transform: "translateZ(0)" }}
      >
        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
        </svg>


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
          <div className="relative w-full sm:w-[380px] h-[88dvh] sm:h-[620px] bg-white rounded-t-3xl sm:rounded-2xl sm:mb-6 sm:mr-5 shadow-2xl flex flex-col overflow-hidden" style={{ willChange: "transform", transform: "translateZ(0)" }}>
            <ChatWidget onClose={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
