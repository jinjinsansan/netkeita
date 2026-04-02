"""Generate real JRA race data JSON for netkeita frontend development.

Usage: python generate_sample_data.py [YYYYMMDD]
Default: 20260329 (last Saturday with data)
"""

import json
import sys
import os
import time

# Add dlogic-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'dlogic-agent'))

from scrapers.jra import fetch_race_list, fetch_race_entries


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "20260329"
    print(f"Fetching JRA races for {date_str}...")

    races = fetch_race_list(date_str)
    if not races:
        print("No races found")
        return

    print(f"Found {len(races)} races")

    # Group by venue
    venues = {}
    for r in races:
        venues.setdefault(r.venue, []).append(r)

    all_races = []
    for venue, venue_races in venues.items():
        print(f"\n{venue}: {len(venue_races)} races")
        for race_summary in sorted(venue_races, key=lambda x: x.race_number):
            print(f"  Fetching {venue} {race_summary.race_number}R {race_summary.race_name}...", end=" ")

            detail = fetch_race_entries(race_summary.race_id)
            time.sleep(0.5)  # be polite

            if not detail:
                print("SKIP (no data)")
                continue

            entries = []
            for e in detail.entries:
                entries.append({
                    "horse_number": e.horse_number,
                    "horse_name": e.horse_name,
                    "jockey": e.jockey,
                    "trainer": e.trainer,
                    "post": e.post,
                    "sex_age": e.sex_age,
                    "weight": e.weight,
                })

            race_data = {
                "race_id": f"{date_str}-{venue}-{race_summary.race_number}",
                "race_id_netkeiba": race_summary.race_id,
                "race_number": race_summary.race_number,
                "race_name": race_summary.race_name or detail.summary.race_name,
                "venue": venue,
                "distance": race_summary.distance or detail.summary.distance,
                "headcount": len(entries),
                "start_time": race_summary.start_time,
                "track_condition": detail.track_condition or "",
                "date": date_str,
                "entries": entries,
            }
            all_races.append(race_data)
            print(f"OK ({len(entries)} horses)")

    # Build output
    output = {
        "date": date_str,
        "formatted_date": f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}",
        "races": all_races,
        "venues": {v: len(r) for v, r in venues.items()},
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'lib', 'sample_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(all_races)} races saved to {out_path}")


if __name__ == "__main__":
    main()
