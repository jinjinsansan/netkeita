"""Tipster (予想家) profile management.

Stores approved/pending tipster profiles in Redis db=6.

Keys:
    nk:tipster:{line_user_id}   string  JSON profile blob
    nk:tipsters:approved        list    approved tipster IDs (newest first)
    nk:tipsters:pending         list    pending application IDs (newest first)
    nk:premium_user:{line_user_id}  string  "1" if user has premium access
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

logger = logging.getLogger(__name__)

_JST = timezone(timedelta(hours=9))
_redis = redis.Redis(host="127.0.0.1", port=6379, db=6, decode_responses=True)

_TIPSTER_KEY_PREFIX = "nk:tipster"
_APPROVED_INDEX = "nk:tipsters:approved"
_PENDING_INDEX = "nk:tipsters:pending"
_PREMIUM_KEY_PREFIX = "nk:premium_user"
_TIPSTER_TTL = 86400 * 365  # 1 year

MAX_CATCHPHRASE_LEN = 60
MAX_DESCRIPTION_LEN = 400
MAX_DISPLAY_NAME_LEN = 50
MAX_SNS_URL_LEN = 200
_ALLOWED_SNS_KEYS = {"x", "youtube", "instagram", "tiktok", "note"}


def _now_iso() -> str:
    return datetime.now(_JST).isoformat()


def _key(line_user_id: str) -> str:
    return f"{_TIPSTER_KEY_PREFIX}:{line_user_id}"


def _premium_key(line_user_id: str) -> str:
    return f"{_PREMIUM_KEY_PREFIX}:{line_user_id}"


def _clean(value: Any, max_len: int) -> str:
    if not value:
        return ""
    return str(value).strip()[:max_len]


# ─────────────────────────────────────────────────────────────────────────────
# Profile read/write
# ─────────────────────────────────────────────────────────────────────────────


def get_tipster(line_user_id: str) -> dict | None:
    try:
        raw = _redis.get(_key(line_user_id))
        return json.loads(raw) if raw else None
    except Exception:
        logger.exception(f"tipsters: failed to read {line_user_id}")
        return None


def list_approved() -> list[dict]:
    """Return all approved tipster profiles newest-first."""
    try:
        ids = _redis.lrange(_APPROVED_INDEX, 0, -1) or []
    except Exception:
        return []
    if not ids:
        return []
    try:
        raws = _redis.mget([_key(i) for i in ids])
    except Exception:
        return []
    result = []
    for raw in raws:
        if raw:
            try:
                result.append(json.loads(raw))
            except Exception:
                pass
    return result


def list_pending() -> list[dict]:
    """Return all pending application profiles newest-first (admin only)."""
    try:
        ids = _redis.lrange(_PENDING_INDEX, 0, -1) or []
    except Exception:
        return []
    if not ids:
        return []
    try:
        raws = _redis.mget([_key(i) for i in ids])
    except Exception:
        return []
    result = []
    for raw in raws:
        if raw:
            try:
                d = json.loads(raw)
                if d.get("status") == "pending":
                    result.append(d)
            except Exception:
                pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Application / approval workflow
# ─────────────────────────────────────────────────────────────────────────────


def apply(
    line_user_id: str,
    display_name: str,
    picture_url: str,
    catchphrase: str,
    description: str,
) -> dict:
    """Submit a new tipster application. Idempotent for the same user."""
    existing = get_tipster(line_user_id)
    if existing and existing.get("status") == "approved":
        return existing

    catchphrase_clean = _clean(catchphrase, MAX_CATCHPHRASE_LEN)
    if not catchphrase_clean:
        raise ValueError("キャッチフレーズは必須です")
    description_clean = _clean(description, MAX_DESCRIPTION_LEN)

    now = _now_iso()
    profile = {
        "line_user_id": line_user_id,
        "display_name": _clean(display_name, MAX_DISPLAY_NAME_LEN) or "名無し",
        "picture_url": picture_url or "",
        "catchphrase": catchphrase_clean,
        "description": description_clean,
        "status": "pending",
        "applied_at": now,
        "approved_at": None,
    }

    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.set(_key(line_user_id), json.dumps(profile, ensure_ascii=False))
        pipe.lrem(_PENDING_INDEX, 0, line_user_id)
        pipe.lpush(_PENDING_INDEX, line_user_id)
        pipe.execute()
    except Exception:
        logger.exception(f"tipsters: apply failed for {line_user_id}")
        raise

    logger.info(f"tipster applied: {display_name} ({line_user_id})")
    return profile


def approve(line_user_id: str) -> dict | None:
    """Approve a pending tipster application."""
    profile = get_tipster(line_user_id)
    if not profile:
        return None
    profile["status"] = "approved"
    profile["approved_at"] = _now_iso()
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.set(_key(line_user_id), json.dumps(profile, ensure_ascii=False))
        pipe.lrem(_PENDING_INDEX, 0, line_user_id)
        pipe.lrem(_APPROVED_INDEX, 0, line_user_id)
        pipe.lpush(_APPROVED_INDEX, line_user_id)
        pipe.execute()
    except Exception:
        logger.exception(f"tipsters: approve failed for {line_user_id}")
        raise
    logger.info(f"tipster approved: {line_user_id}")
    return profile


def reject(line_user_id: str) -> dict | None:
    """Reject a pending tipster application."""
    profile = get_tipster(line_user_id)
    if not profile:
        return None
    profile["status"] = "rejected"
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.set(_key(line_user_id), json.dumps(profile, ensure_ascii=False))
        pipe.lrem(_PENDING_INDEX, 0, line_user_id)
        pipe.execute()
    except Exception:
        logger.exception(f"tipsters: reject failed for {line_user_id}")
        raise
    logger.info(f"tipster rejected: {line_user_id}")
    return profile


def update_profile(
    line_user_id: str,
    *,
    display_name: str | None = None,
    catchphrase: str | None = None,
    description: str | None = None,
    picture_url: str | None = None,
    sns_links: dict | None = None,
) -> dict | None:
    """Let an approved tipster update their own profile."""
    profile = get_tipster(line_user_id)
    if not profile or profile.get("status") != "approved":
        return None
    if display_name is not None:
        cleaned = _clean(display_name, MAX_DISPLAY_NAME_LEN)
        if cleaned:
            profile["display_name"] = cleaned
    if catchphrase is not None:
        profile["catchphrase"] = _clean(catchphrase, MAX_CATCHPHRASE_LEN)
    if description is not None:
        profile["description"] = _clean(description, MAX_DESCRIPTION_LEN)
    if picture_url is not None:
        profile["picture_url"] = picture_url
    if sns_links is not None:
        cleaned_sns: dict = {}
        for k, v in sns_links.items():
            if k in _ALLOWED_SNS_KEYS and isinstance(v, str):
                url = v.strip()[:MAX_SNS_URL_LEN]
                if url:
                    cleaned_sns[k] = url
        profile["sns_links"] = cleaned_sns
    try:
        _redis.set(_key(line_user_id), json.dumps(profile, ensure_ascii=False))
    except Exception:
        logger.exception(f"tipsters: update_profile failed for {line_user_id}")
        raise
    return profile


_MANAGED_ID_PREFIX = "managed_"
_MANAGED_CUSTOM_ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")


def create_managed_tipster(
    display_name: str,
    catchphrase: str,
    description: str = "",
    picture_url: str = "",
    custom_id: str = "",
) -> dict:
    """Admin-only: create (or upsert) a managed tipster.

    If `custom_id` is provided, use ``managed_{custom_id}`` as the ID and
    upsert: an existing profile with the same ID is overwritten, and the
    approved-index is deduplicated (LREM + LPUSH). This makes setup scripts
    idempotent. Without `custom_id` the ID is randomly generated as before.
    """
    import uuid
    if custom_id:
        cid = custom_id.strip().lower()
        if not _MANAGED_CUSTOM_ID_RE.match(cid):
            raise ValueError("custom_id は小文字英数・アンダースコアのみ、40字以内")
        managed_id = f"{_MANAGED_ID_PREFIX}{cid}"
    else:
        managed_id = f"{_MANAGED_ID_PREFIX}{uuid.uuid4().hex}"
    catchphrase_clean = _clean(catchphrase, MAX_CATCHPHRASE_LEN)
    if not catchphrase_clean:
        raise ValueError("キャッチフレーズは必須です")
    now = _now_iso()
    existing = get_tipster(managed_id) if custom_id else None
    applied_at = (existing or {}).get("applied_at") or now
    approved_at = (existing or {}).get("approved_at") or now
    profile = {
        "line_user_id": managed_id,
        "display_name": _clean(display_name, MAX_DISPLAY_NAME_LEN) or "名無し",
        "picture_url": picture_url or "",
        "catchphrase": catchphrase_clean,
        "description": _clean(description, MAX_DESCRIPTION_LEN),
        "status": "approved",
        "is_managed": True,
        "applied_at": applied_at,
        "approved_at": approved_at,
    }
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.set(_key(managed_id), json.dumps(profile, ensure_ascii=False))
        pipe.lrem(_APPROVED_INDEX, 0, managed_id)
        pipe.lpush(_APPROVED_INDEX, managed_id)
        pipe.execute()
    except Exception:
        logger.exception("tipsters: create_managed_tipster failed")
        raise
    logger.info(f"managed tipster upserted: {display_name} ({managed_id})")
    return profile


def is_approved_tipster(line_user_id: str) -> bool:
    profile = get_tipster(line_user_id)
    return bool(profile and profile.get("status") == "approved")


def delete_tipster(line_user_id: str) -> bool:
    """Remove a tipster profile entirely (approved or otherwise)."""
    try:
        pipe = _redis.pipeline(transaction=True)
        pipe.delete(_key(line_user_id))
        pipe.lrem(_APPROVED_INDEX, 0, line_user_id)
        pipe.lrem(_PENDING_INDEX, 0, line_user_id)
        result = pipe.execute()
    except Exception:
        logger.exception(f"tipsters: delete failed for {line_user_id}")
        return False
    deleted = bool(result and result[0])
    if deleted:
        logger.info(f"tipster deleted: {line_user_id}")
    return deleted


# ─────────────────────────────────────────────────────────────────────────────
# Premium access management
# ─────────────────────────────────────────────────────────────────────────────


def grant_premium_access(line_user_id: str) -> None:
    """Grant premium (paid prediction) access to a user."""
    try:
        _redis.set(_premium_key(line_user_id), "1")
        logger.info(f"premium access granted: {line_user_id}")
    except Exception:
        logger.exception(f"tipsters: grant_premium_access failed for {line_user_id}")
        raise


def revoke_premium_access(line_user_id: str) -> None:
    """Revoke premium access from a user."""
    try:
        _redis.delete(_premium_key(line_user_id))
        logger.info(f"premium access revoked: {line_user_id}")
    except Exception:
        logger.exception(f"tipsters: revoke_premium_access failed for {line_user_id}")
        raise


def has_premium_access(line_user_id: str) -> bool:
    try:
        return bool(_redis.get(_premium_key(line_user_id)))
    except Exception:
        return False
