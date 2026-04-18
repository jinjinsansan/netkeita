"""Chat message storage, caching, and pub/sub broadcast.

Redis db=4:
    nk:chat:cache:{channel}          list   recent messages JSON (newest-first)
    nk:chat:pub:{channel}            pubsub broadcast channel
    nk:chat:rl:{line_user_id}        string rate-limit token (TTL 5 s)
    nk:chat:online:{channel}         string connection counter
    nk:user:profile:{line_user_id}   string cached profile JSON (TTL 5 min)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import time
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
RATELIMIT_TTL = 10   # seconds between sends per user
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


# ── Official bot broadcast ─────────────────────────────────────────────────────
# netkeita 公式 bot (運営からのお知らせ・結果速報・波乱警告用) の発言者固定値。
# Rate limit は通さない。is_bot=True フラグをフロント側で拾って装飾する。

BOT_LINE_USER_ID = "bot_netkeita_official"
BOT_NICKNAME = "netkeita公式"
BOT_AVATAR_KEY = "bot"
BOT_AVATAR_EMOJI = "🏇"


def post_bot_message(
    channel: str,
    content: str,
    *,
    avatar_url: str = "",
) -> dict | None:
    """Post an official bot message bypassing rate limits.

    Returns the saved message dict, or None when the channel is invalid or
    the content is empty after trimming.
    """
    if channel not in VALID_CHANNELS:
        return None
    body = (content or "").strip()
    if not body:
        return None
    # キャラクタ上限は通常メッセージと同じ100字
    body = body[:100]
    msg = {
        "id":           secrets.token_urlsafe(8),
        "channel":      channel,
        "line_user_id": BOT_LINE_USER_ID,
        "nickname":     BOT_NICKNAME,
        "avatar_key":   BOT_AVATAR_KEY,
        "avatar_emoji": BOT_AVATAR_EMOJI,
        "avatar_url":   avatar_url or "",
        "content":      body,
        "stamp":        None,
        "reply_to":     None,
        "created_at":   datetime.now(_JST).isoformat(),
        "is_bot":       True,
    }
    try:
        cache_message(channel, msg)
        publish_message(channel, msg)
    except Exception:
        logger.exception("chat: post_bot_message failed")
        return None
    return msg


# ── Pub/sub broadcast ──────────────────────────────────────────────────────────

def publish_message(channel: str, msg: dict) -> None:
    _redis.publish(
        f"{_PUB_PREFIX}:{channel}",
        json.dumps(to_public_msg(msg), ensure_ascii=False),
    )


# ── Online count (ZSET-based, auto-expiring per connection) ──────────────────

_MEMBERS_PREFIX = "nk:chat:members"  # Redis ZSET of conn_ids per channel
_ONLINE_TTL = 90  # seconds before a connection is considered stale


def _online_key(channel: str) -> str:
    return f"{_MEMBERS_PREFIX}:{channel}"


def join_channel(channel: str, conn_id: str) -> int:
    now = time.time()
    key = _online_key(channel)
    _redis.zadd(key, {conn_id: now})
    _redis.expire(key, _ONLINE_TTL * 3)
    return get_online_count(channel)


def touch_channel(channel: str, conn_id: str) -> None:
    key = _online_key(channel)
    _redis.zadd(key, {conn_id: time.time()})
    _redis.expire(key, _ONLINE_TTL * 3)


def leave_channel(channel: str, conn_id: str) -> int:
    key = _online_key(channel)
    _redis.zrem(key, conn_id)
    return get_online_count(channel)


def get_online_count(channel: str) -> int:
    key = _online_key(channel)
    cutoff = time.time() - _ONLINE_TTL
    try:
        _redis.zremrangebyscore(key, 0, cutoff)
    except Exception:
        pass
    return max(0, int(_redis.zcard(key) or 0))


def reset_online_counts() -> None:
    """Delete all member sets (call on startup)."""
    for ch in VALID_CHANNELS:
        _redis.delete(_online_key(ch))


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


_PROFILE_STORE_TTL = 86400 * 180  # 180 days — long-lived but not infinite


def store_profile(line_user_id: str, profile: dict) -> None:
    """Save profile to Redis with a long TTL (reset on every login/update)."""
    _redis.setex(
        f"{_PROFILE_STORE_PREFIX}:{line_user_id}",
        _PROFILE_STORE_TTL,
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
            "message_id":  msg["id"],
            "channel":      channel,
            "line_user_id": msg["line_user_id"],
            "nickname":     msg["nickname"],
            "avatar_key":   msg["avatar_key"],
            "content":      msg.get("content"),
            "stamp":        msg.get("stamp"),
        }).execute()
    except Exception:
        logger.exception("chat: failed to persist message to Supabase")


# ── SSE fan-out hub (single Redis pubsub per channel) ────────────────────────

_STREAM_QUEUE_MAX = 200


class _ChannelStream:
    def __init__(self, channel: str):
        self.channel = channel
        self.queues: set[asyncio.Queue[str]] = set()
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def ensure_task(self) -> None:
        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        ar = get_async_redis()
        pubsub = ar.pubsub()
        await pubsub.subscribe(f"{_PUB_PREFIX}:{self.channel}")
        try:
            while True:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if not msg or msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                for q in list(self.queues):
                    if q.full():
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    try:
                        q.put_nowait(data)
                    except asyncio.QueueFull:
                        pass
        except Exception:
            logger.exception("chat stream hub error")
        finally:
            try:
                await pubsub.unsubscribe(f"{_PUB_PREFIX}:{self.channel}")
                await pubsub.aclose()
            except Exception:
                pass

    def register(self, q: asyncio.Queue[str]) -> None:
        self.queues.add(q)

    def unregister(self, q: asyncio.Queue[str]) -> None:
        self.queues.discard(q)


_STREAMS: dict[str, _ChannelStream] = {}


def _get_stream(channel: str) -> _ChannelStream:
    stream = _STREAMS.get(channel)
    if stream is None:
        stream = _ChannelStream(channel)
        _STREAMS[channel] = stream
    return stream


async def subscribe_stream(channel: str) -> asyncio.Queue[str]:
    stream = _get_stream(channel)
    await stream.ensure_task()
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=_STREAM_QUEUE_MAX)
    stream.register(q)
    return q


def unsubscribe_stream(channel: str, q: asyncio.Queue[str]) -> None:
    stream = _STREAMS.get(channel)
    if stream:
        stream.unregister(q)
