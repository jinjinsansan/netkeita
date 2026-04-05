"use client";

import { useEffect } from "react";

export type ToastKind = "success" | "error" | "info";

export interface ToastMessage {
  id: number;
  kind: ToastKind;
  text: string;
}

const STYLES: Record<ToastKind, { bg: string; border: string; fg: string }> = {
  success: { bg: "#f0f9f0", border: "#1f7a1f", fg: "#1a5c1a" },
  error: { bg: "#fdecea", border: "#c62828", fg: "#a31515" },
  info: { bg: "#e8f1fb", border: "#1565C0", fg: "#0d47a1" },
};

export function Toast({
  toast,
  onDismiss,
  durationMs = 3000,
}: {
  toast: ToastMessage;
  onDismiss: (id: number) => void;
  durationMs?: number;
}) {
  useEffect(() => {
    const id = window.setTimeout(() => onDismiss(toast.id), durationMs);
    return () => window.clearTimeout(id);
  }, [toast.id, durationMs, onDismiss]);

  const s = STYLES[toast.kind];
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto rounded-lg border px-4 py-2.5 text-xs font-bold shadow-lg"
      style={{ backgroundColor: s.bg, borderColor: s.border, color: s.fg }}
    >
      {toast.text}
    </div>
  );
}

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="pointer-events-none fixed top-4 right-4 z-[100] flex flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

// Minimal stateful helper for local (per-page) toast queues.
// Keeps the footprint small — no context provider, no Zustand.
let _toastId = 0;
export function nextToastId(): number {
  _toastId += 1;
  return _toastId;
}
