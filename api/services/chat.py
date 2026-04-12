"""Chat message storage, caching, and pub/sub broadcast.

Redis db=4:
    nk:chat:cache:{channel}          list   recent messages JSON (newest-first)
    nk:chat:pub:{channel}            pubsub broadcast channel
    nk:chat:rl:{line_user_id}        string rate-limit token (TTL 5 s)
    nk:chat:online:{channel}         string connection counter
    nk:user:profile:{line_user_id}   string cached profile JSON (TTL 5 min)
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_JST = timezone(timedelta(hours=9))

_redis = redis.Redis(host="127.0.0.1", port=6379, db=4, decode_responses=True)
_aioredis: aioredis.Redis | None = None

VALID_CHANNELS = {"global", "jra", "nar"}
VALID_STAMPS    = {"🔥", "💰", "😭", "🏇", "👍"}
VALID_AVATARS   = {
    "horse1", "horse2", "jockey1", "jockey2",
    "crown", "fire", "diamond", "clover",
    "thunder", "star", "slot", "eagle",
}
AVATAR_EMOJI: dict[str, str] = {
    "horse1": "🐴", "horse2": "🏇", "jockey1": "🥇", "jockey2": "🎯",
    "crown": "👑",  "fire": "🔥",   "diamond": "💎", "clover": "🍀",
    "thunder": "⚡", "star": "🌟",   "slot": "🎰",   "eagle": "🦅",
}

_CACHE_PREFIX   = "nk:chat:cache"
_PUB_PREFIX     = "nk:chat:pub"
_RL_PREFIX      = "nk:chat:rl"
_ONLINE_PREFIX  = "nk:chat:online"
_PROFILE_PREFIX = "nk:user:profile"

CACHE_MAX     = 50   # messages retained in Redis
RATELIMIT_TTL = 5    # seconds between sends per user
PROFILE_TTL   = 300  # seconds to cache user profile

_PRIVATE_FIELDS = {"line_user_id"}  # never sent to clients


def author_token(line_user_id: str) -> str:
    """Deterministic non-PII token used by clients to identify their own messages."""
    return hashlib.sha256(f"nk:{line_user_id}".encode()).hexdigest()[:16]


def to_public_msg(msg: dict) -> dict:
    """Strip server-only fields before sending to clients."""
    out = {k: v for k, v in msg.items() if k not in _PRIVATE_FIELDS}
    # Attach author_token so clients can detect their own messages
    if "line_user_id" in msg:
        out["author_token"] = author_token(msg["line_user_id"])
    return out


def get_jst_today_start() -> datetime:
    now = datetime.now(_JST)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_async_redis() -> aioredis.Redis:
    global _aioredis
    if _aioredis is None:
        _aioredis = aioredis.Redis(
            host="127.0.0.1", port=6379, db=4, decode_responses=True
        )
    return _aioredis


# ── Rate limiting ──────────────────────────────────────────────────────────────

def check_rate_limit(line_user_id: str) -> bool:
    """Return True if the user may send now, False if rate-limited."""
    key = f"{_RL_PREFIX}:{line_user_id}"
    return _redis.set(key, "1", ex=RATELIMIT_TTL, nx=True) is not None


# ── Message cache ──────────────────────────────────────────────────────────────

def get_cached_messages(channel: str) -> list[dict]:
    """Return up to CACHE_MAX messages, oldest-first."""
    raw = _redis.lrange(f"{_CACHE_PREFIX}:{channel}", 0, CACHE_MAX - 1)
    msgs: list[dict] = []
    for r in reversed(raw):
        try:
            msgs.append(json.loads(r))
        except Exception:
            pass
    return msgs


def cache_message(channel: str, msg: dict) -> None:
    key = f"{_CACHE_PREFIX}:{channel}"
    _redis.lpush(key, json.dumps(to_public_msg(msg), ensure_ascii=False))
    _redis.ltrim(key, 0, CACHE_MAX - 1)


def remove_from_cache(channel: str, msg_id: str) -> None:
    """Remove a single message from the Redis list cache by id."""
    key = f"{_CACHE_PREFIX}:{channel}"
    raw = _redis.lrange(key, 0, -1)
    for r in raw:
        try:
            if json.loads(r).get("id") == msg_id:
                _redis.lrem(key, 0, r)
        except Exception:
            pass


# ── Pub/sub broadcast ──────────────────────────────────────────────────────────

def publish_message(channel: str, msg: dict) -> None:
    _redis.publish(
        f"{_PUB_PREFIX}:{channel}",
        json.dumps(to_public_msg(msg), ensure_ascii=False),
    )


# ── Online count ───────────────────────────────────────────────────────────────

def incr_online(channel: str) -> int:
    key = f"{_ONLINE_PREFIX}:{channel}"
    count = _redis.incr(key)
    _redis.expire(key, 3600)
    return int(count)


def decr_online(channel: str) -> int:
    key = f"{_ONLINE_PREFIX}:{channel}"
    count = _redis.decr(key)
    if count < 0:
        _redis.set(key, 0)
        return 0
    return int(count)


def get_online_count(channel: str) -> int:
    val = _redis.get(f"{_ONLINE_PREFIX}:{channel}")
    return max(0, int(val or 0))


# ── User profile cache ─────────────────────────────────────────────────────────

_PROFILE_STORE_PREFIX = "nk:user:profile:store"  # permanent, no TTL


def get_stored_profile(line_user_id: str) -> dict | None:
    """Permanent profile store (no TTL). Source of truth when Supabase is unavailable."""
    raw = _redis.get(f"{_PROFILE_STORE_PREFIX}:{line_user_id}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def store_profile(line_user_id: str, profile: dict) -> None:
    """Save profile permanently to Redis (no TTL)."""
    _redis.set(
        f"{_PROFILE_STORE_PREFIX}:{line_user_id}",
        json.dumps(profile, ensure_ascii=False),
    )
    # Also refresh the short-lived cache so reads are consistent
    set_cached_profile(line_user_id, profile)


def get_cached_profile(line_user_id: str) -> dict | None:
    raw = _redis.get(f"{_PROFILE_PREFIX}:{line_user_id}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def set_cached_profile(line_user_id: str, profile: dict) -> None:
    _redis.setex(
        f"{_PROFILE_PREFIX}:{line_user_id}",
        PROFILE_TTL,
        json.dumps(profile, ensure_ascii=False),
    )


def invalidate_profile_cache(line_user_id: str) -> None:
    _redis.delete(f"{_PROFILE_PREFIX}:{line_user_id}")


# ── Supabase persistence ───────────────────────────────────────────────────────

def save_message_to_db(channel: str, msg: dict, supabase_client) -> None:
    try:
        supabase_client.table("chat_messages").insert({
            "channel":      channel,
            "line_user_id": msg["line_user_id"],
            "nickname":     msg["nickname"],
            "avatar_key":   msg["avatar_key"],
            "content":      msg.get("content"),
            "stamp":        msg.get("stamp"),
        }).execute()
    except Exception:
        logger.exception("chat: failed to persist message to Supabase")
