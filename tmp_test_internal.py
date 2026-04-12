"""netkeita の _generate_character_predictions と同じ流れで動作確認"""
import sys
sys.path.insert(0, "/opt/dlogic/netkeita-api")

import httpx
from services.data_fetcher import get_race_entries

race_id = "20260408-川崎-11"
date_str = race_id.split("-")[0]

race_data = get_race_entries(date_str, race_id)
if not race_data:
    print("ERROR: get_race_entries returned None")
    sys.exit(1)

entries = race_data.get("entries", [])
print(f"entries count: {len(entries)}")
if entries:
    print(f"sample entry: {entries[0]}")

horse_numbers = [e["horse_number"] for e in entries]
horse_names   = [e.get("horse_name", "") for e in entries]
jockeys       = [e.get("jockey", "") for e in entries]
posts         = [e.get("post", 0) for e in entries]
odds_list     = [float(e.get("odds", 10.0)) for e in entries]

payload = {
    "race_id": race_id,
    "horses": horse_names,
    "horse_numbers": horse_numbers,
    "venue": race_data.get("venue", ""),
    "race_number": race_data.get("race_number", 0),
    "jockeys": jockeys,
    "posts": posts,
    "distance": race_data.get("distance", ""),
    "track_condition": race_data.get("track_condition", "良"),
    "odds": odds_list,
}

print(f"\npayload: race_id={payload['race_id']}, horses={len(payload['horses'])}")

try:
    resp = httpx.post("http://localhost:8000/api/v2/predictions/newspaper", json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    horse_map = dict(zip(horse_numbers, horse_names))
    for engine in ["dlogic", "metalogic", "viewlogic"]:
        top5 = data.get(engine, [])
        names = [f"{n}.{horse_map.get(n,'?')}" for n in top5]
        print(f"{engine}: {names}")
except Exception as e:
    print(f"ERROR calling Dlogic API: {e}")
