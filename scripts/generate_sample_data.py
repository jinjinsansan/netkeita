"""Generate real JRA race data JSON for netkeita frontend development."""

import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'dlogic-agent'))

from scrapers.jra import fetch_race_list, fetch_race_entries

VENUE_CODE = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}


def venue_from_race_id(netkeiba_id: str) -> str:
    code = netkeiba_id[4:6]
    return VENUE_CODE.get(code, '不明')


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else "20260329"
    print(f"Fetching JRA races for {date_str}...")

    races = fetch_race_list(date_str)
    if not races:
        print("No races found")
        return

    print(f"Found {len(races)} races")

    all_races = []
    for race_summary in races:
        venue = venue_from_race_id(race_summary.race_id)
        rnum = race_summary.race_number
        print(f"  {venue} {rnum}R ...", end=" ", flush=True)

        detail = fetch_race_entries(race_summary.race_id)
        time.sleep(0.3)

        if not detail:
            print("SKIP")
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

        race_id = f"{date_str}-{venue}-{rnum}"

        race_data = {
            "race_id": race_id,
            "race_id_netkeiba": race_summary.race_id,
            "race_number": rnum,
            "race_name": detail.summary.race_name or race_summary.race_name,
            "venue": venue,
            "distance": detail.summary.distance or race_summary.distance,
            "headcount": len(entries),
            "start_time": race_summary.start_time,
            "track_condition": detail.track_condition or "",
            "date": date_str,
            "entries": entries,
        }
        all_races.append(race_data)
        print(f"OK ({len(entries)})")

    # Group venues for metadata
    venue_counts = {}
    for r in all_races:
        v = r["venue"]
        venue_counts[v] = venue_counts.get(v, 0) + 1

    output = {
        "date": date_str,
        "formatted_date": f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}",
        "races": all_races,
        "venues": venue_counts,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'lib', 'sample_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(all_races)} races, venues: {venue_counts}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
