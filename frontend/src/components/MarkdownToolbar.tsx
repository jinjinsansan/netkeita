"use client";

import { useCallback, useRef, useState } from "react";
import { uploadArticleImage } from "@/lib/api";

type ToolbarAction =
  | { kind: "wrap"; before: string; after: string; placeholder: string }
  | { kind: "linePrefix"; prefix: string; placeholder: string }
  | { kind: "insert"; text: string };

export interface MarkdownToolbarProps {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (next: string) => void;
  onError?: (message: string) => void;
  /** Visual feedback hook for long-running uploads. */
  onUploadingChange?: (uploading: boolean) => void;
}

/** Button definitions, declared once for readability. */
const BUTTONS: Array<{
  id: string;
  label: string;
  title: string;
  mobileOnly?: boolean;
  action: ToolbarAction;
}> = [
  { id: "h2", label: "H2", title: "見出し (大)", action: { kind: "linePrefix", prefix: "## ", placeholder: "見出し" } },
  { id: "h3", label: "H3", title: "見出し (小)", action: { kind: "linePrefix", prefix: "### ", placeholder: "小見出し" } },
  { id: "bold", label: "B", title: "太字 (Ctrl+B)", action: { kind: "wrap", before: "**", after: "**", placeholder: "太字" } },
  { id: "italic", label: "I", title: "斜体 (Ctrl+I)", action: { kind: "wrap", before: "*", after: "*", placeholder: "斜体" } },
  { id: "list", label: "・", title: "箇条書き", action: { kind: "linePrefix", prefix: "- ", placeholder: "項目" } },
  { id: "ol", label: "1.", title: "番号付きリスト", action: { kind: "linePrefix", prefix: "1. ", placeholder: "項目" } },
  { id: "quote", label: "❝", title: "引用", action: { kind: "linePrefix", prefix: "> ", placeholder: "引用" } },
  { id: "code", label: "</>", title: "インラインコード", action: { kind: "wrap", before: "`", after: "`", placeholder: "code" } },
  { id: "codeblock", label: "```", title: "コードブロック", action: { kind: "wrap", before: "\n```\n", after: "\n```\n", placeholder: "code" } },
  { id: "hr", label: "—", title: "区切り線", action: { kind: "insert", text: "\n\n---\n\n" } },
];

export default function MarkdownToolbar({
  textareaRef,
  value,
  onChange,
  onError,
  onUploadingChange,
}: MarkdownToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);

  // ─── Core mutation: apply an action to the current selection ───────
  const applyAction = useCallback(
    (action: ToolbarAction) => {
      const ta = textareaRef.current;
      if (!ta) return;
      const start = ta.selectionStart ?? value.length;
      const end = ta.selectionEnd ?? value.length;
      const selected = value.slice(start, end);

      let nextValue: string;
      let nextCursor: number;

      if (action.kind === "wrap") {
        const inner = selected || action.placeholder;
        const inserted = `${action.before}${inner}${action.after}`;
        nextValue = value.slice(0, start) + inserted + value.slice(end);
        // Place cursor just before the closing marker if we inserted a
        // placeholder, or after the wrapped selection otherwise.
        nextCursor = selected
          ? start + inserted.length
          : start + action.before.length + inner.length;
      } else if (action.kind === "linePrefix") {
        // Find the start of the current line
        const lineStart = value.lastIndexOf("\n", start - 1) + 1;
        const lineEnd = end;
        const block = value.slice(lineStart, lineEnd);
        // Prefix every non-empty line in the selection.
        const prefixed = block
          .split("\n")
          .map((line) => (line.length > 0 ? action.prefix + line : action.prefix + action.placeholder))
          .join("\n");
        nextValue = value.slice(0, lineStart) + prefixed + value.slice(lineEnd);
        nextCursor = lineStart + prefixed.length;
      } else {
        // "insert"
        nextValue = value.slice(0, start) + action.text + value.slice(end);
        nextCursor = start + action.text.length;
      }

      onChange(nextValue);
      // Restore focus + cursor after React re-renders.
      requestAnimationFrame(() => {
        ta.focus();
        ta.setSelectionRange(nextCursor, nextCursor);
      });
    },
    [textareaRef, value, onChange]
  );

  // ─── Link button: prompt for URL then wrap as [text](url) ──────────
  const handleLink = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart ?? value.length;
    const end = ta.selectionEnd ?? value.length;
    const selected = value.slice(start, end) || "リンクテキスト";
    const url = window.prompt("リンク先 URL を入力してください", "https://");
    if (!url || !/^https?:\/\//i.test(url)) {
      if (url) onError?.("http:// または https:// で始まる URL を入力してください");
      return;
    }
    const inserted = `[${selected}](${url})`;
    const nextValue = value.slice(0, start) + inserted + value.slice(end);
    onChange(nextValue);
    requestAnimationFrame(() => {
      ta.focus();
      const cursor = start + inserted.length;
      ta.setSelectionRange(cursor, cursor);
    });
  }, [textareaRef, value, onChange, onError]);

  // ─── Image button: open file picker → upload → insert ![](url) ─────
  const handleImageClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleImageSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      // Always clear the input so picking the same file twice still fires change.
      e.target.value = "";
      if (!file) return;

      setUploading(true);
      onUploadingChange?.(true);
      try {
        const res = await uploadArticleImage(file);
        if (!res.success || !res.url) {
          onError?.(res.error || "画像アップロードに失敗しました");
          return;
        }
        const alt = file.name.replace(/\.[^.]+$/, "") || "image";
        const ta = textareaRef.current;
        const start = ta?.selectionStart ?? value.length;
        const end = ta?.selectionEnd ?? value.length;
        const inserted = `\n![${alt}](${res.url})\n`;
        const nextValue = value.slice(0, start) + inserted + value.slice(end);
        onChange(nextValue);
        requestAnimationFrame(() => {
          if (!ta) return;
          ta.focus();
          const cursor = start + inserted.length;
          ta.setSelectionRange(cursor, cursor);
        });
      } finally {
        setUploading(false);
        onUploadingChange?.(false);
      }
    },
    [textareaRef, value, onChange, onError, onUploadingChange]
  );

  return (
    <div
      className="sticky top-0 z-20 -mx-1 px-1 py-1.5 bg-white/95 backdrop-blur border-b border-[#e5e5e5] flex flex-wrap items-center gap-1"
      role="toolbar"
      aria-label="マークダウン編集ツールバー"
    >
      {BUTTONS.map((btn) => (
        <button
          key={btn.id}
          type="button"
          title={btn.title}
          aria-label={btn.title}
          onClick={() => applyAction(btn.action)}
          className="min-w-[40px] h-10 md:h-9 px-2 text-sm font-bold text-[#333] bg-white hover:bg-[#f0f7f0] active:bg-[#e0efe0] border border-[#d0d0d0] rounded transition select-none"
        >
          {btn.label}
        </button>
      ))}
      <button
        type="button"
        title="リンク"
        aria-label="リンク挿入"
        onClick={handleLink}
        className="min-w-[40px] h-10 md:h-9 px-2 text-sm font-bold text-[#333] bg-white hover:bg-[#f0f7f0] active:bg-[#e0efe0] border border-[#d0d0d0] rounded transition select-none"
      >
        🔗
      </button>
      <button
        type="button"
        title={uploading ? "アップロード中..." : "画像"}
        aria-label="画像アップロード"
        disabled={uploading}
        onClick={handleImageClick}
        className="min-w-[40px] h-10 md:h-9 px-2 text-sm font-bold text-[#1f7a1f] bg-[#f0f7f0] hover:bg-[#e0efe0] active:bg-[#d0e5d0] border border-[#1f7a1f] rounded transition select-none disabled:opacity-50 disabled:cursor-wait"
      >
        {uploading ? "⏳" : "🖼 画像"}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleImageSelected}
        className="hidden"
      />
    </div>
  );
}
