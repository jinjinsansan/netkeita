#!/usr/bin/env python3
"""Pre-fetch course stats for all JRA races on a given date.

Reads prefetch JSON to get race_id_netkeiba, then scrapes netkeiba
for course performance data and caches in Redis.

Usage:
    python scripts/prefetch_course_stats.py              # Today
    python scripts/prefetch_course_stats.py 20260405     # Specific date
"""

import json
import os
import sys
import time
from datetime import datetime

_LINEBOT_ROOT = "/opt/dlogic/linebot"
_API_ROOT = "/opt/dlogic/netkeita-api"

if _LINEBOT_ROOT not in sys.path:
    sys.path.insert(0, _LINEBOT_ROOT)
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

PREFETCH_DIR = os.path.join(_LINEBOT_ROOT, "data", "prefetch")

from services.course_stats_scraper import fetch_course_stats_for_race


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    path = os.path.join(PREFETCH_DIR, f"races_{date_str}.json")

    if not os.path.exists(path):
        print(f"Prefetch not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    races = [r for r in data.get("races", [])
             if not r.get("is_local", False) and r.get("race_id_netkeiba")]

    print(f"[{datetime.now().isoformat()}] Course stats prefetch for {date_str}: {len(races)} JRA races")

    for i, race in enumerate(races):
        nid = race["race_id_netkeiba"]
        venue = race.get("venue", "")
        rnum = race.get("race_number", "")
        print(f"  [{i+1}/{len(races)}] {venue}{rnum}R ({nid})...", end=" ", flush=True)

        start = time.time()
        stats = fetch_course_stats_for_race(nid)
        elapsed = time.time() - start
        total_with_data = sum(1 for v in stats.values() if v)
        print(f"{total_with_data}/{len(stats)} horses ({elapsed:.1f}s)")

        time.sleep(1)  # Be polite

    print(f"[{datetime.now().isoformat()}] Done")


if __name__ == "__main__":
    main()
