#!/usr/bin/env python3
"""Update odds in prefetch JSON files for today's JRA races.

Reads existing prefetch JSON, fetches latest odds via Lightpanda/Playwright,
and updates the odds arrays in-place. Designed to run every 10 minutes on race days.

Usage:
    python scripts/update_odds.py              # Today
    python scripts/update_odds.py 20260405     # Specific date
"""

import json
import os
import sys
import time
from datetime import datetime

_PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from scrapers.odds import fetch_jra_odds_batch

PREFETCH_DIR = os.path.join(_PROJECT_ROOT, "data", "prefetch")
# netkeita API uses a separate copy
API_PREFETCH_DIR = "/root/dlogic-agent/data/prefetch"


def update_odds(date_str: str) -> bool:
    path = os.path.join(PREFETCH_DIR, f"races_{date_str}.json")
    if not os.path.exists(path):
        print(f"Prefetch file not found: {path}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    races = data.get("races", [])
    jra_races = [r for r in races if not r.get("is_local", False) and r.get("race_id_netkeiba")]

    if not jra_races:
        print("No JRA races found in prefetch")
        return False

    netkeiba_ids = [r["race_id_netkeiba"] for r in jra_races]
    print(f"Fetching odds for {len(netkeiba_ids)} JRA races...")

    start = time.time()
    odds_results = fetch_jra_odds_batch(netkeiba_ids)
    elapsed = time.time() - start
    print(f"Odds fetched in {elapsed:.1f}s ({len(odds_results)}/{len(netkeiba_ids)} races)")

    updated = 0
    for race in jra_races:
        nid = race["race_id_netkeiba"]
        if nid in odds_results:
            odds_map = odds_results[nid]
            new_odds = []
            for hn in race.get("horse_numbers", []):
                new_odds.append(odds_map.get(hn, 0.0))
            if any(o > 0 for o in new_odds):
                race["odds"] = new_odds
                updated += 1

    if updated > 0:
        data["metadata"]["odds_updated_at"] = datetime.now().isoformat()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Updated odds for {updated} races -> {path}")

        # Copy to netkeita API prefetch dir
        api_path = os.path.join(API_PREFETCH_DIR, f"races_{date_str}.json")
        if os.path.isdir(API_PREFETCH_DIR):
            with open(api_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"Copied to API dir -> {api_path}")
    else:
        print("No odds updated")

    return updated > 0


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
    print(f"[{datetime.now().isoformat()}] Updating odds for {date_str}")
    update_odds(date_str)


if __name__ == "__main__":
    main()
