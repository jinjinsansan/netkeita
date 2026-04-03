"""Rewrite stable comments using Claude to avoid copyright issues."""

import logging
import anthropic
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# In-memory cache: (horse_number, comment_hash) -> rewritten
_rewrite_cache: dict[str, dict] = {}

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


def rewrite_comment(horse_number: int, stable_data: dict) -> dict:
    """Rewrite a single horse's stable comment. Returns modified stable_data."""
    if not stable_data or not stable_data.get("comment"):
        return stable_data

    cache_key = f"{horse_number}:{stable_data.get('comment', '')[:50]}"
    if cache_key in _rewrite_cache:
        return _rewrite_cache[cache_key]

    if not _client:
        logger.warning("Anthropic client not available, returning original")
        return stable_data

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

        import json
        # Extract JSON from response
        if "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            parsed = json.loads(json_str)
            result = {
                **stable_data,
                "comment": parsed.get("comment", stable_data["comment"]),
                "status": parsed.get("status", stable_data.get("status", "")),
            }
        else:
            result = {**stable_data, "comment": text}

        _rewrite_cache[cache_key] = result
        return result

    except Exception:
        logger.exception(f"Rewrite failed for horse #{horse_number}")
        return stable_data
