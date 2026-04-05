"use client";

import { useEffect } from "react";

export interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "OK",
  cancelLabel = "キャンセル",
  danger,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  // Dismiss on Escape for keyboard accessibility
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-[400px] bg-white rounded-xl shadow-2xl p-5">
        <h3 id="confirm-modal-title" className="text-sm font-bold text-[#222] mb-2">
          {title}
        </h3>
        <p className="text-xs text-[#555] leading-relaxed mb-5 whitespace-pre-wrap">
          {message}
        </p>
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="text-xs font-bold text-[#666] hover:text-[#333] px-4 py-2 rounded-lg transition"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`text-xs font-bold text-white px-4 py-2 rounded-lg transition ${
              danger
                ? "bg-[#c62828] hover:bg-[#a31515]"
                : "bg-[#1f7a1f] hover:bg-[#16611a]"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
