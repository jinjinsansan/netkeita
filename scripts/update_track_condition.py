#!/usr/bin/env python3
"""Update track_condition in prefetch files by re-scraping race entry pages.

Runs as a cron job several times on race day (after 09:00 when tracks are
officially announced) to pull the latest baba/track condition without
re-running the full prefetch.

Usage:
    python update_track_condition.py [YYYYMMDD]
    (defaults to today in JST)
"""
import json
import os
import sys
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Make linebot scrapers importable
sys.path.insert(0, "/opt/dlogic/linebot")

try:
    from scrapers.jra import fetch_race_entries as jra_fetch
    from scrapers.nar import fetch_race_entries as nar_fetch
except Exception as e:
    print(f"FATAL: cannot import scrapers: {e}", file=sys.stderr)
    sys.exit(1)

PREFETCH_DIR = Path("/opt/dlogic/linebot/data/prefetch")
JST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def today_str() -> str:
    return datetime.now(JST).strftime("%Y%m%d")


def update_prefetch(date_str: str) -> None:
    path = PREFETCH_DIR / f"races_{date_str}.json"
    if not path.exists():
        logger.warning(f"prefetch file not found: {path}")
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    races = data.get("races") if isinstance(data, dict) else data
    if not isinstance(races, list):
        logger.error("unexpected prefetch structure")
        return

    updated = 0
    skipped_known = 0
    failed = 0

    for r in races:
        current = r.get("track_condition", "")
        # Only refetch races where track is still unknown
        if current and current not in ("−", "-", "", "不明", "?", "？"):
            skipped_known += 1
            continue

        race_id = r.get("race_id_netkeiba") or r.get("race_id", "")
        is_local = bool(r.get("is_local"))
        venue = r.get("venue", "")
        rno = r.get("race_number", "?")

        if not race_id:
            failed += 1
            continue

        try:
            fn = nar_fetch if is_local else jra_fetch
            detail = fn(race_id)
            if not detail:
                failed += 1
                continue
            new_cond = getattr(detail, "track_condition", None)
            if new_cond and new_cond not in ("−", "-", "", "不明", "?", "？"):
                r["track_condition"] = new_cond
                updated += 1
                logger.info(f"  {venue} {rno}R: {new_cond}")
            # Polite throttle
            time.sleep(0.4)
        except Exception as e:
            logger.warning(f"  {venue} {rno}R: fetch error {e}")
            failed += 1

    if updated:
        # Atomic write
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(path)

    logger.info(
        f"date={date_str} updated={updated} skipped_known={skipped_known} "
        f"failed={failed} total={len(races)}"
    )


def clear_matrix_cache() -> None:
    """Restart netkeita-api to clear in-memory matrix cache so that the
    updated track_condition takes effect immediately."""
    try:
        import subprocess
        subprocess.run(
            ["systemctl", "restart", "netkeita-api"],
            check=False, timeout=15,
        )
        logger.info("netkeita-api restarted (matrix cache cleared)")
    except Exception as e:
        logger.warning(f"cache clear failed: {e}")


def main() -> None:
    date_str = sys.argv[1] if len(sys.argv) > 1 else today_str()
    logger.info(f"=== update_track_condition start date={date_str} ===")
    update_prefetch(date_str)
    clear_matrix_cache()
    logger.info("=== done ===")


if __name__ == "__main__":
    main()
