"""Fetch race data from prefetch files and Dlogic backend API."""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

from config import DLOGIC_API_URL, PREFETCH_DIR

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
_client = httpx.Client(timeout=30)


def get_today_str() -> str:
    return datetime.now(JST).strftime("%Y%m%d")


def get_available_dates() -> list[str]:
    """Return list of available prefetch dates (JRA only, newest first)."""
    if not os.path.isdir(PREFETCH_DIR):
        return []
    dates = []
    for fname in os.listdir(PREFETCH_DIR):
        if fname.startswith("races_") and fname.endswith(".json"):
            date_str = fname.replace("races_", "").replace(".json", "")
            if len(date_str) == 8 and date_str.isdigit():
                # Only include files that have JRA races
                pf = load_prefetch(date_str)
                if pf:
                    jra_races = [r for r in pf.get("races", []) if not r.get("is_local", False)]
                    if jra_races:
                        dates.append(date_str)
    return sorted(dates, reverse=True)


def load_prefetch(date_str: str) -> dict | None:
    path = os.path.join(PREFETCH_DIR, f"races_{date_str}.json")
    if not os.path.exists(path):
        logger.warning(f"Prefetch not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Failed to load prefetch: {path}")
        return None


def get_races(date_str: str) -> list[dict]:
    """Get JRA race list for a date. Returns list of race summaries."""
    pf = load_prefetch(date_str)
    if not pf:
        return []

    races = pf.get("races", [])
    # Filter JRA only (not local/NAR)
    jra_races = [r for r in races if not r.get("is_local", False)]

    result = []
    for r in jra_races:
        result.append({
            "race_id": r.get("race_id", ""),
            "race_number": r.get("race_number", 0),
            "race_name": r.get("race_name", ""),
            "venue": r.get("venue", ""),
            "distance": r.get("distance", ""),
            "headcount": len(r.get("horses", [])),
            "start_time": r.get("start_time", ""),
            "track_condition": r.get("track_condition", ""),
        })
    return result


def get_race_entries(date_str: str, race_id: str) -> dict | None:
    """Get entries for a specific race from prefetch."""
    pf = load_prefetch(date_str)
    if not pf:
        return None

    for r in pf.get("races", []):
        if r.get("race_id") == race_id:
            entries = []
            horses = r.get("horses", [])
            nums = r.get("horse_numbers", [])
            jockeys = r.get("jockeys", [])
            posts = r.get("posts", [])
            for i in range(len(horses)):
                entries.append({
                    "horse_number": nums[i] if i < len(nums) else i + 1,
                    "horse_name": horses[i],
                    "jockey": jockeys[i] if i < len(jockeys) else "",
                    "post": posts[i] if i < len(posts) else 0,
                })
            return {
                "race_id": race_id,
                "race_name": r.get("race_name", ""),
                "venue": r.get("venue", ""),
                "distance": r.get("distance", ""),
                "race_number": r.get("race_number", 0),
                "track_condition": r.get("track_condition", ""),
                "entries": entries,
            }
    return None


def get_odds_from_prefetch(date_str: str, race_id: str) -> dict:
    """Get odds data from prefetch file. Returns {horse_number: odds_value}."""
    pf = load_prefetch(date_str)
    if not pf:
        return {}

    for r in pf.get("races", []):
        if r.get("race_id") == race_id:
            odds_list = r.get("odds", [])
            nums = r.get("horse_numbers", [])
            result = {}
            for i, num in enumerate(nums):
                if i < len(odds_list):
                    try:
                        result[num] = float(odds_list[i])
                    except (ValueError, TypeError):
                        pass
            return result
    return {}


def get_internet_predictions(race_name: str) -> dict | None:
    """Get internet predictions for a race from prefetch files."""
    import glob as _glob
    import re as _re
    safe_name = _re.sub(r'[^\w]', '_', race_name)
    pattern = os.path.join(PREFETCH_DIR, f"internet_predictions_{safe_name}_*.json")
    files = sorted(_glob.glob(pattern), reverse=True)

    if not files:
        all_files = sorted(_glob.glob(os.path.join(PREFETCH_DIR, "internet_predictions_*.json")), reverse=True)
        for f in all_files:
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                if race_name in data.get("race_name", ""):
                    return data
            except Exception:
                continue
        return None

    try:
        with open(files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Failed to load internet predictions: {files[0]}")
        return None


def get_full_scores(race_data: dict) -> dict:
    """Call full-scores API. Returns all horses' engine scores + track_adjustment."""
    payload = _build_payload(race_data)
    try:
        resp = _client.post(
            f"{DLOGIC_API_URL}/api/v2/predictions/full-scores",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception("Full-scores API call failed")
        return {}


def get_predictions(race_data: dict) -> dict:
    """Call predictions API. Returns newspaper response (legacy)."""
    payload = _build_payload(race_data)
    try:
        resp = _client.post(
            f"{DLOGIC_API_URL}/api/v2/predictions/newspaper",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception("Predictions API call failed")
        return {}


def get_analysis(endpoint: str, race_data: dict) -> dict:
    """Call analysis API (race-flow, jockey, bloodline, recent-runs)."""
    payload = _build_payload(race_data)
    try:
        resp = _client.post(
            f"{DLOGIC_API_URL}{endpoint}",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception(f"Analysis API call failed: {endpoint}")
        return {}


def get_horse_recent_runs(race_data: dict, horse_number: int) -> list[dict]:
    """Get recent 5 runs for a single horse via backend API."""
    entry = next((e for e in race_data.get("entries", []) if e["horse_number"] == horse_number), None)
    if not entry:
        return []
    payload = _build_payload(race_data)
    payload["horses"] = [entry["horse_name"]]
    payload["horse_numbers"] = [horse_number]
    try:
        resp = _client.post(
            f"{DLOGIC_API_URL}/api/v2/analysis/recent-runs",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for h in data.get("horses", []):
            if h.get("horse_number") == horse_number:
                return h.get("runs", [])
    except Exception:
        logger.exception(f"Recent runs API failed for horse #{horse_number}")
    return []


def get_horse_bloodline(race_data: dict, horse_number: int) -> dict:
    """Get bloodline analysis for a single horse via backend API."""
    entry = next((e for e in race_data.get("entries", []) if e["horse_number"] == horse_number), None)
    if not entry:
        return {}
    payload = _build_payload(race_data)
    payload["horses"] = [entry["horse_name"]]
    payload["horse_numbers"] = [horse_number]
    try:
        resp = _client.post(
            f"{DLOGIC_API_URL}/api/v2/analysis/bloodline-analysis",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for h in data.get("bloodline", []):
            if h.get("horse_number") == horse_number:
                return h
    except Exception:
        logger.exception(f"Bloodline API failed for horse #{horse_number}")
    return {}


def get_stable_comments(date_str: str, venue: str, race_number: int) -> dict:
    """Get stable/trainer comments from keibabook via linebot scraper."""
    import sys
    sys.path.insert(0, "/opt/dlogic/linebot")
    try:
        from scrapers.stable_comment import fetch_comments_for_race
        result = fetch_comments_for_race(date_str, venue, race_number, is_chihou=False)
        return result or {}
    except Exception:
        logger.exception("Stable comments fetch failed")
        return {}


def _build_payload(race_data: dict) -> dict:
    """Build standard payload for backend API calls."""
    return {
        "race_id": race_data.get("race_id", ""),
        "horses": [e["horse_name"] for e in race_data.get("entries", [])],
        "horse_numbers": [e["horse_number"] for e in race_data.get("entries", [])],
        "jockeys": [e.get("jockey", "") for e in race_data.get("entries", [])],
        "posts": [e.get("post", 0) for e in race_data.get("entries", [])],
        "venue": race_data.get("venue", ""),
        "race_number": race_data.get("race_number", 0),
        "distance": race_data.get("distance", ""),
        "track_condition": race_data.get("track_condition", "良"),
    }
