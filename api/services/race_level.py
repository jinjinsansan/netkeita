"""Race Level service — look up S/A/B/C/D level for past races.

Data is populated by scripts/calc_race_level.py (weekly batch from PC-KEIBA DB)
and stored in Redis db=3 with key prefix ``nk:racelevel:``.

Two key formats are stored per race:
  - ``nk:racelevel:{YYYYMMDD}_{venue}_{race_bango}`` (primary, always unique)
  - ``nk:racelevel:{YYYYMMDD}_{venue}_{race_name}`` (secondary, for name lookup)

This module enriches recent_runs returned by horse-detail API with
``race_level``, ``race_level_detail`` fields.
"""

import json
import logging
import redis as _redis

logger = logging.getLogger(__name__)

_r = _redis.Redis(host="127.0.0.1", port=6379, db=3, decode_responses=True)
_PREFIX = "nk:racelevel"


def _normalize_date(date_str: str) -> str:
    """'2026/03/05' or '20260305' → '20260305'."""
    return date_str.replace("/", "")[:8] if date_str else ""


def get_race_level(date_str: str, venue: str, race_name: str) -> dict | None:
    """Look up race level from Redis by date + venue + race_name."""
    d = _normalize_date(date_str)
    if not d or not venue:
        return None

    # Try name-based key first (works for named races like 重賞/特別)
    if race_name and race_name.strip():
        try:
            raw = _r.get(f"{_PREFIX}:{d}_{venue}_{race_name.strip()}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    # Fallback: scan for date+venue prefix (for unnamed races)
    try:
        pattern = f"{_PREFIX}:{d}_{venue}_*"
        for key in _r.scan_iter(pattern, count=20):
            raw = _r.get(key)
            if raw:
                data = json.loads(raw)
                if race_name and data.get("race_name", "").strip() == race_name.strip():
                    return data
    except Exception:
        pass

    return None


def enrich_recent_runs(runs: list[dict]) -> list[dict]:
    """Add race_level fields to each run (in-place + return).

    Each run gets:
      - race_level: str (S/A/B/C/D) or None
      - race_level_detail: {win: "3/12", place: "6/12"} or None
    """
    if not runs:
        return runs

    # Build keys for batch lookup
    name_keys = []
    for run in runs:
        d = _normalize_date(run.get("date", ""))
        venue = run.get("venue", "")
        race_name = (run.get("race_name") or "").strip()
        if d and venue and race_name:
            name_keys.append(f"{_PREFIX}:{d}_{venue}_{race_name}")
        else:
            name_keys.append("")

    # Batch lookup with pipeline
    try:
        pipe = _r.pipeline(transaction=False)
        for k in name_keys:
            if k:
                pipe.get(k)
            else:
                pipe.get("__nonexistent__")
        results = pipe.execute()
    except Exception:
        logger.exception("race_level pipeline failed")
        results = [None] * len(name_keys)

    for i, run in enumerate(runs):
        raw = results[i] if i < len(results) else None
        if raw:
            try:
                data = json.loads(raw)
                run["race_level"] = data.get("level")
                run["race_level_detail"] = {
                    "win": f"{data.get('win_count', 0)}/{data.get('win_total', 0)}",
                    "place": f"{data.get('place_count', 0)}/{data.get('place_total', 0)}",
                }
                continue
            except Exception:
                pass

        # Fallback: try individual lookup for unnamed races
        d = _normalize_date(run.get("date", ""))
        venue = run.get("venue", "")
        race_name = (run.get("race_name") or "").strip()
        if d and venue:
            data = get_race_level(run.get("date", ""), venue, race_name)
            if data:
                run["race_level"] = data.get("level")
                run["race_level_detail"] = {
                    "win": f"{data.get('win_count', 0)}/{data.get('win_total', 0)}",
                    "place": f"{data.get('place_count', 0)}/{data.get('place_total', 0)}",
                }
                continue

        run["race_level"] = None
        run["race_level_detail"] = None

    return runs
