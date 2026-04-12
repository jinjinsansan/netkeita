import json, sys, time
from datetime import datetime

sys.path.insert(0, "/opt/dlogic/netkeita-api")
sys.path.insert(0, "/opt/dlogic/linebot")
from services.course_stats_scraper import fetch_course_stats_for_race

date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d")
path = f"/opt/dlogic/linebot/data/prefetch/races_{date_str}.json"

with open(path, "r") as f:
    data = json.load(f)

races = [r for r in data.get("races", [])
         if not r.get("is_local", False) and r.get("race_id_netkeiba")]

print(f"[{datetime.now().isoformat()}] Course stats for {date_str}: {len(races)} races")

for i, race in enumerate(races):
    nid = race["race_id_netkeiba"]
    venue = race.get("venue", "")
    rnum = race.get("race_number", "")
    print(f"  [{i+1}/{len(races)}] {venue}{rnum}R ({nid})...", end=" ", flush=True)
    start = time.time()
    stats = fetch_course_stats_for_race(nid)
    elapsed = time.time() - start
    n = sum(1 for v in stats.values() if v)
    print(f"{n}/{len(stats)} horses ({elapsed:.1f}s)")
    time.sleep(1)

print(f"[{datetime.now().isoformat()}] Done")
