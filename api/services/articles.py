"""Article storage service for the note-style posting feature.

Stores each article as a JSON blob in Redis db=5 and maintains a sorted
index of slugs so the list endpoint can render in reverse-chronological
order without an expensive SCAN.

Keys:
    nk:article:{slug}       string  JSON blob of the article
    nk:articles:index       list    slugs newest-first (LPUSH / LREM)

Schema stored on disk (internal):
    {
        "slug": str,
        "title": str,
        "description": str,
        "body": str,                 # markdown
        "thumbnail_url": str,
        "author": str,               # display name of the admin who wrote it
        "author_id": str,            # LINE user id — PRIVATE, never serialised publicly
        "status": "published" | "draft",
        "created_at": str,           # ISO8601 JST
        "updated_at": str,
    }

Public serialisation (what API callers receive) is produced by
`public_view()` / `admin_view()` so author_id never leaks unless the
caller is the admin themselves.

Correctness guarantees:
    * Slug creation uses SET NX so two concurrent creates can't
      overwrite each other (TOCTOU closed).
    * list_articles uses MGET to batch reads into a single roundtrip.
    * list_articles self-heals orphan index entries (LREM on None).
    * Optimistic locking: update_article accepts expected_updated_at and
      raises ConflictError when the stored value has moved on.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

logger = logging.getLogger(__name__)

_JST = timezone(timedelta(hours=9))
_redis = redis.Redis(host="127.0.0.1", port=6379, db=5, decode_responses=True)

_ARTICLE_KEY_PREFIX = "nk:article"
_INDEX_KEY = "nk:articles:index"

# Slug format: lowercase alphanumerics, hyphen, underscore. 1-80 chars.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
# Characters allowed when auto-generating a slug from a title.
_SLUG_SANITISE_RE = re.compile(r"[^a-z0-9]+")

# Thumbnail URL scheme whitelist — blocks data:, javascript:, file:, etc.
_ALLOWED_URL_SCHEMES = ("http://", "https://")

# Reasonable length caps to guard against hostile payloads.
MAX_TITLE_LEN = 200
MAX_DESCRIPTION_LEN = 500
MAX_BODY_LEN = 100_000  # 100 KB of markdown is plenty
MAX_THUMBNAIL_LEN = 1000
MAX_PREVIEW_BODY_LEN = 300
MAX_BET_METHOD_LEN = 100

# Reading time estimation: ~400 Japanese characters per minute is typical
# for casual readers. Used by public_view() for "◯分で読める" display.
_CHARS_PER_MINUTE = 400

# Upper bound for slug collision retries when auto-generating.
_SLUG_RETRY_LIMIT = 10


class ConflictError(Exception):
    """Raised when an optimistic-lock update is stale."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(_JST).isoformat()


def _article_key(slug: str) -> str:
    return f"{_ARTICLE_KEY_PREFIX}:{slug}"


def _safe_url(value: str) -> str:
    """Return the URL if it uses an allowed scheme, otherwise empty string."""
    if not value:
        return ""
    v = value.strip()
    lower = v.lower()
    if not any(lower.startswith(s) for s in _ALLOWED_URL_SCHEMES):
        return ""
    return v


def is_valid_slug(slug: str) -> bool:
    return bool(slug) and bool(_SLUG_RE.match(slug))


def _slug_base_from_title(title: str, fallback: str = "article") -> str:
    norm = unicodedata.normalize("NFKD", title or "")
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = _SLUG_SANITISE_RE.sub("-", ascii_only).strip("-")
    cleaned = cleaned[:50]
    return cleaned or fallback


def generate_slug(title: str, fallback_prefix: str = "article") -> str:
    """Create a URL-safe slug from a Japanese/English title.

    Strategy:
      1. NFKD-normalise the title to strip diacritics
      2. Lowercase and keep [a-z0-9]; collapse other runs to hyphen
      3. Append a compact YYMMDDHHmm timestamp so collisions are rare

    Note: create_article() still does a full NX check and numeric retry
    so this function never has to guarantee global uniqueness on its own.
    """
    base = _slug_base_from_title(title, fallback_prefix)
    stamp = datetime.now(_JST).strftime("%y%m%d%H%M")  # 10 chars
    return f"{base}-{stamp}"


def _clean_str(value: Any, *, max_len: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    stripped = value.strip()
    return stripped[:max_len]


def _validate_status(status: str) -> str:
    return "draft" if status == "draft" else "published"


def _estimate_reading_time(body: str) -> int:
    """Return the estimated reading time in minutes (minimum 1)."""
    if not body:
        return 1
    # Strip markdown punctuation to count meaningful characters
    chars = len(re.sub(r"\s+", "", body))
    return max(1, (chars + _CHARS_PER_MINUTE - 1) // _CHARS_PER_MINUTE)


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation views — strictly separate "public" and "admin" shapes so
# author_id (LINE user id) never leaks to anonymous readers.
# ─────────────────────────────────────────────────────────────────────────────


_PUBLIC_FIELDS = (
    "slug", "title", "description", "body", "thumbnail_url",
    "author", "status", "created_at", "updated_at", "race_id",
    # prediction-specific fields
    "content_type", "tipster_id", "bet_method", "ticket_count",
    "preview_body", "is_premium",
    # AI-generated prediction fields (auto-posted by managed tipsters)
    "ai_generated", "ai_model", "picks",
)

_PUBLIC_SUMMARY_FIELDS = (
    "slug", "title", "description", "thumbnail_url",
    "author", "status", "created_at", "updated_at", "race_id",
    # prediction-specific fields
    "content_type", "tipster_id", "bet_method", "ticket_count",
    "preview_body", "is_premium",
    # AI-generated prediction fields
    "ai_generated", "ai_model",
)


def public_view(record: dict, has_premium: bool = False) -> dict:
    """Strip private fields (author_id) from a full record.

    For premium predictions, body is only included when has_premium=True.
    """
    if not record:
        return {}
    out = {k: record.get(k, "") for k in _PUBLIC_FIELDS}
    out["reading_time_minutes"] = _estimate_reading_time(out.get("body", ""))
    if out.get("is_premium") and not has_premium:
        out["body"] = ""  # gate body behind premium access
    return out


def admin_view(record: dict) -> dict:
    """Include every field, for admin edit screens and audit trails."""
    if not record:
        return {}
    out = dict(record)
    out["reading_time_minutes"] = _estimate_reading_time(out.get("body", ""))
    return out


def public_summary(record: dict) -> dict:
    if not record:
        return {}
    out = {k: record.get(k, "") for k in _PUBLIC_SUMMARY_FIELDS}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Read path
# ─────────────────────────────────────────────────────────────────────────────


def _read_raw(slug: str) -> dict | None:
    try:
        raw = _redis.get(_article_key(slug))
        return json.loads(raw) if raw else None
    except Exception:
        logger.exception(f"articles: failed to read {slug}")
        return None


def get_article_raw(slug: str) -> dict | None:
    """Return the raw stored record (admin-only internal use)."""
    if not is_valid_slug(slug):
        return None
    return _read_raw(slug)


def get_article(slug: str) -> dict | None:
    """Alias for `get_article_raw`. Kept for call-site compatibility."""
    return get_article_raw(slug)


def list_articles(
    *, include_drafts: bool = False, limit: int = 50, offset: int = 0
) -> dict:
    """Return paginated article summaries newest-first.

    Performance: uses MGET to fetch all article JSONs in a single roundtrip,
    eliminating the previous O(n) GET loop. Orphan index entries (where
    the JSON has been deleted but the index still holds the slug) are
    self-healed via LREM.

    Returns:
        {
            "items":       list[public_summary dict],
            "total_count": int,         # number of matching articles
            "has_more":    bool,        # True if more pages exist beyond offset+limit
            "offset":      int,
            "limit":       int,
        }
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    try:
        slugs = _redis.lrange(_INDEX_KEY, 0, -1) or []
    except Exception:
        logger.exception("articles: failed to read index")
        return {"items": [], "total_count": 0, "has_more": False, "offset": offset, "limit": limit}

    if not slugs:
        return {"items": [], "total_count": 0, "has_more": False, "offset": offset, "limit": limit}

    # Batch MGET — one roundtrip regardless of list size.
    try:
        keys = [_article_key(s) for s in slugs]
        raws = _redis.mget(keys)
    except Exception:
        logger.exception("articles: mget failed")
        raws = [None] * len(slugs)

    filtered: list[dict] = []
    orphans: list[str] = []

    for slug, raw in zip(slugs, raws):
        if raw is None:
            orphans.append(slug)
            continue
        try:
            data = json.loads(raw)
        except Exception:
            logger.warning(f"articles: corrupt json for {slug}; treating as orphan")
            orphans.append(slug)
            continue
        if not include_drafts and data.get("status") != "published":
            continue
        filtered.append(data)

    # Self-heal: remove orphans from the index (best effort, never blocks).
    if orphans:
        try:
            pipe = _redis.pipeline(transaction=False)
            for slug in orphans:
                pipe.lrem(_INDEX_KEY, 0, slug)
            pipe.execute()
            logger.info(f"articles: self-healed {len(orphans)} orphan index entries")
        except Exception:
            logger.exception("articles: self-heal failed")

    total_count = len(filtered)
    window = filtered[offset : offset + limit]
    has_more = (offset + limit) < total_count

    return {
        "items": [public_summary(d) for d in window],
        "total_count": total_count,
        "has_more": has_more,
        "offset": offset,
        "limit": limit,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Write path
# ─────────────────────────────────────────────────────────────────────────────


def _try_create(slug: str, payload: str) -> bool:
    """Atomic SET NX for an article. Returns True on success."""
    try:
        return bool(_redis.set(_article_key(slug), payload, nx=True))
    except Exception:
        logger.exception(f"articles: SET NX failed for {slug}")
        return False


MAX_AI_MODEL_LEN = 100


def _sanitize_picks(value: Any) -> dict:
    """Coerce picks to a safe {str: int} dict, dropping invalid entries.

    Accepts arbitrary input (dict / None / junk) and returns at most 10
    valid integer picks keyed by short alphanumeric strings. This keeps
    the record schema stable against malformed AI output.
    """
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, int] = {}
    for k, v in list(value.items())[:10]:
        if not isinstance(k, str) or not k or len(k) > 20:
            continue
        # Keys must be simple identifiers (no spaces, control chars)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", k):
            continue
        if isinstance(v, bool):
            continue  # bool is a subclass of int — reject explicitly
        if isinstance(v, int) and 1 <= v <= 30:
            cleaned[k] = v
    return cleaned


def create_article(
    *,
    title: str,
    description: str,
    body: str,
    thumbnail_url: str,
    status: str,
    author: str,
    author_id: str,
    slug: str | None = None,
    race_id: str = "",
    content_type: str = "article",
    tipster_id: str = "",
    bet_method: str = "",
    ticket_count: int = 0,
    preview_body: str = "",
    is_premium: bool = False,
    ai_generated: bool = False,
    ai_model: str = "",
    picks: dict | None = None,
) -> dict:
    """Create a new article. Returns the saved dict.

    Raises ValueError on validation problems.

    Concurrency guarantee: uses SET NX so two simultaneous creates on the
    same slug never clobber each other. Auto-generated slugs retry up to
    _SLUG_RETRY_LIMIT times with numeric suffixes before giving up.
    """
    title_clean = _clean_str(title, max_len=MAX_TITLE_LEN)
    if not title_clean:
        raise ValueError("タイトルは必須です")

    description_clean = _clean_str(description, max_len=MAX_DESCRIPTION_LEN)
    body_clean = _clean_str(body, max_len=MAX_BODY_LEN)
    if not body_clean:
        raise ValueError("本文は必須です")

    thumbnail_clean = _safe_url(_clean_str(thumbnail_url, max_len=MAX_THUMBNAIL_LEN))
    status_clean = _validate_status(status)

    # Resolve candidate slugs
    user_supplied_slug = slug is not None and slug.strip() != ""
    if user_supplied_slug:
        slug_candidate = slug.strip().lower()
        if not is_valid_slug(slug_candidate):
            raise ValueError(
                "スラッグは半角英数字・ハイフン・アンダースコアのみ使用できます"
            )
        candidates = [slug_candidate]
    else:
        base = generate_slug(title_clean)
        candidates = [base] + [f"{base}-{i}" for i in range(2, _SLUG_RETRY_LIMIT + 2)]

    now = _now_iso()
    race_id_clean = _clean_str(race_id, max_len=100)
    record_template = {
        "title": title_clean,
        "description": description_clean,
        "body": body_clean,
        "thumbnail_url": thumbnail_clean,
        "author": _clean_str(author, max_len=100),
        "author_id": _clean_str(author_id, max_len=100),
        "status": status_clean,
        "race_id": race_id_clean,
        "created_at": now,
        "updated_at": now,
        "content_type": content_type if content_type in ("article", "prediction") else "article",
        "tipster_id": _clean_str(tipster_id, max_len=100),
        "bet_method": _clean_str(bet_method, max_len=MAX_BET_METHOD_LEN),
        "ticket_count": max(0, int(ticket_count)) if isinstance(ticket_count, (int, float)) else 0,
        "preview_body": _clean_str(preview_body, max_len=MAX_PREVIEW_BODY_LEN),
        "is_premium": bool(is_premium),
        "ai_generated": bool(ai_generated),
        "ai_model": _clean_str(ai_model, max_len=MAX_AI_MODEL_LEN),
        "picks": _sanitize_picks(picks),
    }

    chosen_slug: str | None = None
    record: dict | None = None

    for candidate in candidates:
        record = {"slug": candidate, **record_template}
        payload = json.dumps(record, ensure_ascii=False)
        if _try_create(candidate, payload):
            chosen_slug = candidate
            break

    if chosen_slug is None or record is None:
        if user_supplied_slug:
            raise ValueError(
                f"スラッグ '{candidates[0]}' は既に使用されています"
            )
        raise ValueError("スラッグの自動生成に失敗しました。時間をおいて再実行してください")

    # Index update — separate step because SET NX already succeeded. LREM
    # first is a safety net against double-index entries from legacy data.
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.lrem(_INDEX_KEY, 0, chosen_slug)
        pipe.lpush(_INDEX_KEY, chosen_slug)
        pipe.execute()
    except Exception:
        logger.exception(f"articles: failed to index {chosen_slug}; rolling back")
        try:
            _redis.delete(_article_key(chosen_slug))
        except Exception:
            pass
        raise

    logger.info(f"article created: {chosen_slug} by {author_id}")
    return record


def update_article(
    slug: str,
    *,
    title: str | None = None,
    description: str | None = None,
    body: str | None = None,
    thumbnail_url: str | None = None,
    status: str | None = None,
    race_id: str | None = None,
    expected_updated_at: str | None = None,
    bet_method: str | None = None,
    ticket_count: int | None = None,
    preview_body: str | None = None,
    is_premium: bool | None = None,
) -> dict | None:
    """Update an existing article in place.

    If `expected_updated_at` is provided and does not match the stored
    value, raises ConflictError — the caller should refresh and retry.

    Returns the updated dict, or None when the article doesn't exist.
    """
    if not is_valid_slug(slug):
        raise ValueError("スラッグが不正です")

    current = _read_raw(slug)
    if current is None:
        return None

    if expected_updated_at is not None and expected_updated_at != current.get("updated_at"):
        raise ConflictError(
            "この記事は別の管理者によって更新されています。ページを再読み込みしてください"
        )

    if title is not None:
        title_clean = _clean_str(title, max_len=MAX_TITLE_LEN)
        if not title_clean:
            raise ValueError("タイトルは必須です")
        current["title"] = title_clean
    if description is not None:
        current["description"] = _clean_str(description, max_len=MAX_DESCRIPTION_LEN)
    if body is not None:
        body_clean = _clean_str(body, max_len=MAX_BODY_LEN)
        if not body_clean:
            raise ValueError("本文は必須です")
        current["body"] = body_clean
    if thumbnail_url is not None:
        current["thumbnail_url"] = _safe_url(
            _clean_str(thumbnail_url, max_len=MAX_THUMBNAIL_LEN)
        )
    if status is not None:
        current["status"] = _validate_status(status)
    if race_id is not None:
        current["race_id"] = _clean_str(race_id, max_len=100)
    if bet_method is not None:
        current["bet_method"] = _clean_str(bet_method, max_len=MAX_BET_METHOD_LEN)
    if ticket_count is not None:
        current["ticket_count"] = max(0, int(ticket_count))
    if preview_body is not None:
        current["preview_body"] = _clean_str(preview_body, max_len=MAX_PREVIEW_BODY_LEN)
    if is_premium is not None:
        current["is_premium"] = bool(is_premium)

    current["updated_at"] = _now_iso()

    try:
        _redis.set(_article_key(slug), json.dumps(current, ensure_ascii=False))
    except Exception:
        logger.exception(f"articles: failed to update {slug}")
        raise

    logger.info(f"article updated: {slug}")
    return current


def get_articles_by_race_id(race_id: str) -> list[dict]:
    """Return published articles linked to a specific race_id."""
    if not race_id:
        return []
    try:
        slugs = _redis.lrange(_INDEX_KEY, 0, -1) or []
    except Exception:
        return []
    if not slugs:
        return []
    try:
        keys = [_article_key(s) for s in slugs]
        raws = _redis.mget(keys)
    except Exception:
        return []
    results = []
    for raw in raws:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if data.get("status") == "published" and data.get("race_id") == race_id:
            results.append(public_summary(data))
    return results


def list_predictions_by_tipster(tipster_id: str) -> list[dict]:
    """Return published predictions for a specific tipster (newest first)."""
    if not tipster_id:
        return []
    try:
        slugs = _redis.lrange(_INDEX_KEY, 0, -1) or []
    except Exception:
        return []
    if not slugs:
        return []
    try:
        raws = _redis.mget([_article_key(s) for s in slugs])
    except Exception:
        return []
    results = []
    for raw in raws:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if (
            data.get("status") == "published"
            and data.get("tipster_id") == tipster_id
        ):
            results.append(public_summary(data))
    return results


def delete_article(slug: str) -> bool:
    if not is_valid_slug(slug):
        return False
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.delete(_article_key(slug))
        pipe.lrem(_INDEX_KEY, 0, slug)
        result = pipe.execute()
    except Exception:
        logger.exception(f"articles: failed to delete {slug}")
        return False
    deleted = bool(result and result[0])
    if deleted:
        logger.info(f"article deleted: {slug}")
    return deleted


__all__ = [
    "ConflictError",
    "admin_view",
    "create_article",
    "delete_article",
    "generate_slug",
    "get_article",
    "get_article_raw",
    "get_articles_by_race_id",
    "is_valid_slug",
    "list_articles",
    "public_summary",
    "public_view",
    "update_article",
    "list_predictions_by_tipster",
    "MAX_BODY_LEN",
    "MAX_DESCRIPTION_LEN",
    "MAX_THUMBNAIL_LEN",
    "MAX_TITLE_LEN",
    "MAX_PREVIEW_BODY_LEN",
    "MAX_BET_METHOD_LEN",
]
