"""Rewrite stable comments using Claude to avoid copyright issues.

Uses Redis for cross-worker cache sharing. Attempts sync rewrite with
a timeout; falls back to original and writes cache in background.
"""

import json
import hashlib
import logging
import threading
import anthropic
import redis

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
_redis = redis.Redis(host="127.0.0.1", port=6379, db=4, decode_responses=True)
_CACHE_TTL = 86400  # 24 hours
_REWRITE_TIMEOUT = 0.5  # seconds — return original if slower, bg thread caches for next request


def _build_prompt(trainer: str, comment: str, status: str) -> str:
    return (
        "あなたは競馬の関係者コメントをリライトするアシスタントです。\n"
        "以下の関係者コメントを、意味と情報を保ちつつ完全に別の表現に書き換えてください。\n\n"
        "ルール:\n"
        "- 元の文章をそのまま使わず、自分の言葉で書き直す\n"
        "- 馬の状態、調教の評価、注目ポイントなどの情報は正確に保つ\n"
        "- 簡潔に、1〜2文程度にまとめる\n"
        "- 専門用語はそのまま使ってOK\n"
        '- JSON形式で返す: {"comment": "リライトした文章", "status": "状態を2〜4文字で要約"}\n\n'
        f"元のコメント:\n"
        f"調教師: {trainer}\n"
        f"コメント: {comment}\n"
        f"状態: {status}"
    )


def _cache_key(horse_number: int, comment: str) -> str:
    h = hashlib.md5(comment.encode()).hexdigest()[:12]
    return f"nk:rewrite:{horse_number}:{h}"


def _do_rewrite_and_cache(key: str, horse_number: int, stable_data: dict):
    """Call Claude API and store result in Redis."""
    try:
        prompt = _build_prompt(
            trainer=stable_data.get("trainer", ""),
            comment=stable_data.get("comment", ""),
            status=stable_data.get("status", ""),
        )
        resp = _client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        if "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            parsed = json.loads(json_str)
            result = {
                "comment": parsed.get("comment", stable_data["comment"]),
                "status": parsed.get("status", stable_data.get("status", "")),
            }
        else:
            result = {"comment": text}

        _redis.setex(key, _CACHE_TTL, json.dumps(result, ensure_ascii=False))
        logger.info(f"Rewrite done for horse #{horse_number}")
        return result
    except Exception:
        logger.exception(f"Rewrite failed for horse #{horse_number}")
        return None


def rewrite_comment(horse_number: int, stable_data: dict) -> dict:
    """Rewrite with timeout. Returns rewritten data if fast enough, else original."""
    if not stable_data or not stable_data.get("comment"):
        return stable_data

    if not _client:
        return stable_data

    key = _cache_key(horse_number, stable_data["comment"])

    # Check Redis cache first
    try:
        cached = _redis.get(key)
        if cached:
            return {**stable_data, **json.loads(cached)}
    except Exception:
        pass

    # Try sync rewrite with timeout
    result_holder = [None]

    def _worker():
        result_holder[0] = _do_rewrite_and_cache(key, horse_number, stable_data)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=_REWRITE_TIMEOUT)

    if result_holder[0]:
        return {**stable_data, **result_holder[0]}

    # Timeout — return original, background thread will cache when done
    return stable_data
