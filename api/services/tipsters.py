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
    try:
        _redis.set(_key(line_user_id), json.dumps(profile, ensure_ascii=False))
    except Exception:
        logger.exception(f"tipsters: update_profile failed for {line_user_id}")
        raise
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
