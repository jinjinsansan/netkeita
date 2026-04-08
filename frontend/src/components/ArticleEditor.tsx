"use client";

import {
  useCallback,
  useDeferredValue,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import type { ArticleInput } from "@/lib/api";
import { fetchRaces, uploadArticleImage } from "@/lib/api";
import type { RaceSummary } from "@/lib/types";
import ConfirmModal from "./ConfirmModal";
import MarkdownToolbar from "./MarkdownToolbar";

type Mode = "edit" | "preview";

// Server-side caps mirrored here so the UI can warn users before they
// hit a 400 error. Values must stay in sync with api/services/articles.py.
const MAX_TITLE_LEN = 200;
const MAX_DESCRIPTION_LEN = 500;
const MAX_BODY_LEN = 100_000;

const AUTOSAVE_INTERVAL_MS = 5000;
const AUTOSAVE_KEY_PREFIX = "nk:article:autosave";

export interface ArticleEditorProps {
  /** Stable identifier for the autosave bucket. "new" for create, slug for edit. */
  autosaveKey: string;
  initial?: Partial<ArticleInput>;
  submitting?: boolean;
  submitLabel?: string;
  showDelete?: boolean;
  slugEditable?: boolean;
  /** Previous updated_at, sent back for optimistic locking. */
  expectedUpdatedAt?: string;
  onSubmit: (input: ArticleInput) => void | Promise<void>;
  onDelete?: () => void | Promise<void>;
  onCancel?: () => void;
}

interface AutosavePayload {
  title: string;
  description: string;
  body: string;
  thumbnailUrl: string;
  slug: string;
  savedAt: string;
}

export default function ArticleEditor({
  autosaveKey,
  initial,
  submitting,
  submitLabel = "公開",
  showDelete,
  slugEditable = true,
  expectedUpdatedAt,
  onSubmit,
  onDelete,
  onCancel,
}: ArticleEditorProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [slug, setSlug] = useState(initial?.slug ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [thumbnailUrl, setThumbnailUrl] = useState(initial?.thumbnail_url ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [raceId, setRaceId] = useState(initial?.race_id ?? "");
  const [races, setRaces] = useState<RaceSummary[]>([]);
  const [mode, setMode] = useState<Mode>("edit");
  const [localError, setLocalError] = useState<string | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [draftRestoredAt, setDraftRestoredAt] = useState<string | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  const dirtyRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [thumbUploading, setThumbUploading] = useState(false);
  const thumbInputRef = useRef<HTMLInputElement | null>(null);
  const storageKey = `${AUTOSAVE_KEY_PREFIX}:${autosaveKey}`;

  // Load races for the race selector dropdown.
  // Always fetch today. If the article already has a race_id from a different
  // date, also fetch that date so the saved value appears in the list.
  useEffect(() => {
    const toDateStr = (d: Date) =>
      `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;

    const today = toDateStr(new Date());
    const savedRaceId = initial?.race_id ?? "";
    // race_id format: "YYYYMMDD-venue-num"
    const savedDate = savedRaceId ? savedRaceId.split("-")[0] : "";
    const datesToFetch = savedDate && savedDate !== today
      ? [today, savedDate]
      : [today];

    Promise.all(datesToFetch.map((d) => fetchRaces(d))).then((results) => {
      const seen = new Set<string>();
      const all: RaceSummary[] = [];
      for (const data of results) {
        for (const v of data.venues) {
          for (const r of v.races) {
            if (!seen.has(r.race_id)) {
              seen.add(r.race_id);
              all.push(r);
            }
          }
        }
      }
      setRaces(all);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Deferred value for preview — stops the markdown parser from running on
  // every keystroke for large documents.
  const deferredBody = useDeferredValue(body);

  // ── One-shot: restore autosave on mount ────────────────────────────────
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const saved = JSON.parse(raw) as AutosavePayload;
      if (!saved) return;
      // Only offer restore when the draft differs from the initial prop values
      const initialBody = initial?.body ?? "";
      const initialTitle = initial?.title ?? "";
      if (saved.body === initialBody && saved.title === initialTitle) return;
      if (
        window.confirm(
          `前回の未保存下書きが見つかりました (${saved.savedAt})。復元しますか？`
        )
      ) {
        setTitle(saved.title || initialTitle);
        setDescription(saved.description || initial?.description || "");
        setBody(saved.body || initialBody);
        setThumbnailUrl(saved.thumbnailUrl || initial?.thumbnail_url || "");
        if (slugEditable) setSlug(saved.slug || initial?.slug || "");
        setDraftRestoredAt(saved.savedAt);
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Mark dirty whenever any editable field changes ─────────────────────
  useEffect(() => {
    dirtyRef.current = true;
  }, [title, slug, description, thumbnailUrl, body]);

  // ── Autosave to localStorage ───────────────────────────────────────────
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!dirtyRef.current) return;
      try {
        const savedAt = new Date().toLocaleTimeString("ja-JP", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        const payload: AutosavePayload = {
          title,
          description,
          body,
          thumbnailUrl,
          slug,
          savedAt,
        };
        window.localStorage.setItem(storageKey, JSON.stringify(payload));
        setLastSavedAt(savedAt);
      } catch {
        /* ignore quota errors */
      }
    }, AUTOSAVE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [title, description, body, thumbnailUrl, slug, storageKey]);

  // ── beforeunload warning when the form is dirty ────────────────────────
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirtyRef.current) return;
      e.preventDefault();
      // Modern browsers ignore the custom string but still show their own.
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const submit = useCallback(
    async (status: "published" | "draft") => {
      if (!title.trim()) {
        setLocalError("タイトルを入力してください");
        return;
      }
      if (!body.trim()) {
        setLocalError("本文を入力してください");
        return;
      }
      if (title.length > MAX_TITLE_LEN) {
        setLocalError(`タイトルは${MAX_TITLE_LEN}文字以内にしてください`);
        return;
      }
      if (body.length > MAX_BODY_LEN) {
        setLocalError(`本文は${MAX_BODY_LEN.toLocaleString()}文字以内にしてください`);
        return;
      }
      setLocalError(null);
      try {
        await onSubmit({
          title: title.trim(),
          description: description.trim(),
          body,
          thumbnail_url: thumbnailUrl.trim(),
          status,
          slug: slug.trim() || undefined,
          race_id: raceId || undefined,
          expected_updated_at: expectedUpdatedAt,
        });
        // On successful submit, clear autosave and mark clean
        dirtyRef.current = false;
        try {
          window.localStorage.removeItem(storageKey);
        } catch {
          /* ignore */
        }
      } catch {
        /* onSubmit handles its own errors */
      }
    },
    [title, body, description, thumbnailUrl, slug, expectedUpdatedAt, onSubmit, storageKey]
  );

  // ── Inline markdown wrappers for keyboard shortcuts ────────────────────
  const wrapSelection = useCallback(
    (before: string, after: string, placeholder: string) => {
      const ta = textareaRef.current;
      if (!ta) return;
      const start = ta.selectionStart ?? body.length;
      const end = ta.selectionEnd ?? body.length;
      const selected = body.slice(start, end) || placeholder;
      const inserted = `${before}${selected}${after}`;
      const next = body.slice(0, start) + inserted + body.slice(end);
      setBody(next);
      requestAnimationFrame(() => {
        ta.focus();
        const cursor = start + inserted.length;
        ta.setSelectionRange(cursor, cursor);
      });
    },
    [body]
  );

  // ── Ctrl+S / ⌘+S saves as draft; Ctrl+B / Ctrl+I format selection ──────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        submit("draft");
        return;
      }
      // Only format shortcuts when the textarea is the active element so we
      // don't hijack Ctrl+B in other inputs.
      if (document.activeElement !== textareaRef.current) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        wrapSelection("**", "**", "太字");
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "i") {
        e.preventDefault();
        wrapSelection("*", "*", "斜体");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [submit, wrapSelection]);

  const handleDeleteClick = () => setConfirmDeleteOpen(true);
  const handleConfirmDelete = async () => {
    setConfirmDeleteOpen(false);
    if (onDelete) {
      dirtyRef.current = false;
      try {
        window.localStorage.removeItem(storageKey);
      } catch {
        /* ignore */
      }
      await onDelete();
    }
  };

  const handleThumbUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setThumbUploading(true);
    setLocalError(null);
    const res = await uploadArticleImage(file);
    if (res.success && res.url) {
      setThumbnailUrl(res.url);
    } else {
      setLocalError(res.error || "サムネイルのアップロードに失敗しました");
    }
    setThumbUploading(false);
    if (thumbInputRef.current) thumbInputRef.current.value = "";
  };

  const titleCount = title.length;
  const descCount = description.length;
  const bodyCount = body.length;
  const isThumbValid = thumbnailUrl.startsWith("http://") || thumbnailUrl.startsWith("https://");

  const counterColor = (used: number, max: number): string => {
    const pct = used / max;
    if (pct >= 1) return "text-[#c62828]";
    if (pct >= 0.9) return "text-[#F57C00]";
    return "text-[#999]";
  };

  return (
    <div className="max-w-[1200px] mx-auto">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h1 className="text-lg font-black text-[#222]">
          {showDelete ? "記事を編集" : "新しい記事"}
        </h1>
        <div className="flex items-center gap-2">
          {lastSavedAt && (
            <span className="text-[10px] text-[#999] hidden sm:inline">
              自動保存: {lastSavedAt}
            </span>
          )}
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="text-xs font-bold text-[#666] hover:text-[#333] px-3 py-2"
            >
              キャンセル
            </button>
          )}
          <button
            type="button"
            disabled={submitting}
            onClick={() => submit("draft")}
            className="text-xs font-bold text-[#1f7a1f] border border-[#1f7a1f] hover:bg-[#f0f7f0] px-3 py-2 rounded-lg transition disabled:opacity-40"
            title="Ctrl+S / ⌘+S"
          >
            下書き保存
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => submit("published")}
            className="text-xs font-bold bg-[#1f7a1f] hover:bg-[#16611a] text-white px-4 py-2 rounded-lg shadow-sm transition disabled:opacity-40"
          >
            {submitting ? "送信中..." : submitLabel}
          </button>
          {showDelete && onDelete && (
            <button
              type="button"
              disabled={submitting}
              onClick={handleDeleteClick}
              className="text-xs font-bold text-[#c62828] border border-[#c62828] hover:bg-[#fdecea] px-3 py-2 rounded-lg transition disabled:opacity-40"
            >
              削除
            </button>
          )}
        </div>
      </div>

      {draftRestoredAt && (
        <div className="mb-3 rounded-lg bg-[#fff3e0] border border-[#F57C00] px-3 py-2 text-xs text-[#a85c00]">
          未保存下書きを復元しました ({draftRestoredAt})
        </div>
      )}

      <div className="bg-white border border-[#d0d0d0] rounded-lg p-4 mb-4 space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">
              タイトル <span className="text-[#c62828]">*</span>
            </label>
            <span className={`text-[10px] ${counterColor(titleCount, MAX_TITLE_LEN)}`}>
              {titleCount} / {MAX_TITLE_LEN}
            </span>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value.slice(0, MAX_TITLE_LEN + 20))}
            placeholder="記事タイトル"
            maxLength={MAX_TITLE_LEN + 20}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            対象レース (任意)
          </label>
          <select
            value={raceId}
            onChange={(e) => setRaceId(e.target.value)}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f] bg-white"
          >
            <option value="">レースを選択しない</option>
            {races.map((r) => (
              <option key={r.race_id} value={r.race_id}>
                {r.venue} {r.race_number}R {r.race_name} ({r.distance}, {r.headcount}頭)
              </option>
            ))}
          </select>
          {raceId && (
            <p className="text-[10px] text-[#1f7a1f] mt-0.5">
              この記事はレースページの「プレミア予想」ボタンからもアクセスできます
            </p>
          )}
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            スラッグ (URL)
          </label>
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase())}
            disabled={!slugEditable}
            placeholder="未入力なら自動生成 (half-width英数字・ハイフン・アンダースコア)"
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#1f7a1f] disabled:bg-[#f5f5f5] disabled:text-[#888]"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-bold text-[#444]">
              説明文 (OGP 用)
            </label>
            <span className={`text-[10px] ${counterColor(descCount, MAX_DESCRIPTION_LEN)}`}>
              {descCount} / {MAX_DESCRIPTION_LEN}
            </span>
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value.slice(0, MAX_DESCRIPTION_LEN + 20))}
            placeholder="一覧ページとSNSシェア時に表示される説明文"
            rows={2}
            className="w-full border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
          />
        </div>

        <div>
          <label className="block text-[11px] font-bold text-[#444] mb-1">
            サムネイル
          </label>
          <div className="flex gap-2">
            <input
              type="url"
              value={thumbnailUrl}
              onChange={(e) => setThumbnailUrl(e.target.value)}
              placeholder="URLを入力 または 画像をアップロード"
              className="flex-1 border border-[#d0d0d0] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#1f7a1f]"
            />
            <button
              type="button"
              onClick={() => thumbInputRef.current?.click()}
              disabled={thumbUploading}
              className="shrink-0 bg-[#1f7a1f] hover:bg-[#165a16] text-white text-[11px] font-bold px-3 py-2 rounded transition disabled:opacity-50"
            >
              {thumbUploading ? "送信中..." : "画像を選択"}
            </button>
            <input
              ref={thumbInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={handleThumbUpload}
              className="hidden"
            />
          </div>
          {thumbnailUrl && !isThumbValid && (
            <p className="mt-1 text-[10px] text-[#c62828]">
              http:// または https:// で始まる URL を入力してください
            </p>
          )}
          {thumbnailUrl && isThumbValid && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={thumbnailUrl}
              alt="サムネイルプレビュー"
              className="mt-2 max-h-32 rounded border border-[#e5e5e5] object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          )}
        </div>
      </div>

      <div className="md:hidden mb-2 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setMode("edit")}
          className={`flex-1 text-xs font-bold px-3 py-2 rounded transition ${
            mode === "edit"
              ? "bg-[#1f7a1f] text-white"
              : "bg-white border border-[#d0d0d0] text-[#666]"
          }`}
        >
          編集
        </button>
        <button
          type="button"
          onClick={() => setMode("preview")}
          className={`flex-1 text-xs font-bold px-3 py-2 rounded transition ${
            mode === "preview"
              ? "bg-[#1f7a1f] text-white"
              : "bg-white border border-[#d0d0d0] text-[#666]"
          }`}
        >
          プレビュー
        </button>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className={`${mode === "edit" ? "block" : "hidden"} md:block`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold text-[#444]">本文</span>
            <span className={`text-[10px] ${counterColor(bodyCount, MAX_BODY_LEN)}`}>
              {bodyCount.toLocaleString()} / {MAX_BODY_LEN.toLocaleString()}
            </span>
          </div>
          <div className="border border-[#d0d0d0] rounded overflow-hidden bg-white">
            <MarkdownToolbar
              textareaRef={textareaRef}
              value={body}
              onChange={setBody}
              onError={setLocalError}
              onUploadingChange={setImageUploading}
            />
            <textarea
              ref={textareaRef}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="ここに本文を書いてください。上のボタンで見出しや画像を簡単に挿入できます。"
              rows={20}
              autoCapitalize="sentences"
              autoCorrect="off"
              spellCheck={false}
              className="w-full p-3 text-[15px] md:text-sm leading-relaxed focus:outline-none min-h-[420px] md:min-h-[480px] resize-y"
            />
          </div>
          {imageUploading && (
            <p className="mt-1 text-[10px] text-[#1f7a1f]">画像をアップロード中...</p>
          )}
          <p className="mt-1 text-[10px] text-[#999] leading-relaxed">
            ショートカット: Ctrl+B 太字 · Ctrl+I 斜体 · Ctrl+S 下書き保存
          </p>
        </div>
        <div className={`${mode === "preview" ? "block" : "hidden"} md:block`}>
          <div className="text-[11px] font-bold text-[#444] mb-1">プレビュー</div>
          <div className="border border-[#d0d0d0] rounded p-4 bg-white min-h-[480px] prose-nk">
            {deferredBody.trim() ? (
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{deferredBody}</ReactMarkdown>
            ) : (
              <p className="text-xs text-[#bbb]">ここにプレビューが表示されます</p>
            )}
          </div>
        </div>
      </div>

      {localError && (
        <div
          className="mt-3 rounded-lg bg-[#fdecea] border border-[#f5c6cb] px-3 py-2 text-xs text-[#a33]"
          role="alert"
        >
          {localError}
        </div>
      )}

      <ConfirmModal
        open={confirmDeleteOpen}
        title="記事を削除"
        message="この記事を完全に削除します。この操作は取り消せません。"
        confirmLabel="削除する"
        danger
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </div>
  );
}
