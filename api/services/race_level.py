"""Race Level service — look up S/A/B/C/D level for past races.

Data is populated by scripts/scrape_race_level.py (weekly batch) and stored
in Redis db=3 with key prefix ``nk:racelevel:``.

This module provides a lightweight lookup used by the horse-detail API to
enrich recent_runs with a ``race_level`` field.
"""

import json
import logging
import redis as _redis

logger = logging.getLogger(__name__)

_r = _redis.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
_PREFIX = "nk:racelevel"

LEVEL_LABELS = {
    "S": "超ハイレベル",
    "A": "ハイレベル",
    "B": "標準以上",
    "C": "標準",
    "D": "低レベル",
    "?": "データなし",
}


def _normalize_date(date_str: str) -> str:
    """'2026/03/05' or '20260305' → '20260305'."""
    return date_str.replace("/", "")[:8] if date_str else ""


def _make_key(date_str: str, venue: str, race_name: str) -> str:
    d = _normalize_date(date_str)
    return f"{d}_{venue}_{race_name}"


def get_race_level(date_str: str, venue: str, race_name: str) -> dict | None:
    """Look up race level from Redis.

    Returns dict with level, win/place stats, or None if not found.
    """
    key = _make_key(date_str, venue, race_name)
    if not key or key.startswith("_"):
        return None
    try:
        raw = _r.get(f"{_PREFIX}:{key}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def enrich_recent_runs(runs: list[dict]) -> list[dict]:
    """Add race_level field to each run in the list (in-place + return).

    Each run is expected to have 'date', 'venue', 'race_name' keys.
    Adds 'race_level' (str: S/A/B/C/D/?) and 'race_level_detail' (dict).
    """
    if not runs:
        return runs

    # Batch lookup with pipeline for efficiency
    keys = []
    for run in runs:
        k = _make_key(run.get("date", ""), run.get("venue", ""), run.get("race_name", ""))
        keys.append(f"{_PREFIX}:{k}" if k and not k.startswith("_") else "")

    try:
        pipe = _r.pipeline(transaction=False)
        for k in keys:
            if k:
                pipe.get(k)
            else:
                pipe.get("__nonexistent__")
        results = pipe.execute()
    except Exception:
        logger.exception("race_level pipeline failed")
        results = [None] * len(keys)

    for i, run in enumerate(runs):
        raw = results[i] if i < len(results) else None
        if raw:
            try:
                data = json.loads(raw)
                run["race_level"] = data.get("level", "?")
                run["race_level_detail"] = {
                    "win": f"{data.get('win_count', 0)}/{data.get('win_total', 0)}",
                    "place": f"{data.get('place_count', 0)}/{data.get('place_total', 0)}",
                }
            except Exception:
                run["race_level"] = None
                run["race_level_detail"] = None
        else:
            run["race_level"] = None
            run["race_level_detail"] = None

    return runs
