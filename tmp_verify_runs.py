"""Verify recent runs data matches the correct horse for ALL horses in a race."""
import json, urllib.request, sys

race_id = sys.argv[1] if len(sys.argv) > 1 else "20260404-%E4%B8%AD%E5%B1%B1-11"

# Get race entries first
entries_url = f"http://localhost:5002/api/race/{race_id}/matrix"
matrix = json.loads(urllib.request.urlopen(entries_url, timeout=30).read())

horses = matrix.get("horses", [])
print(f"=== Race {race_id}: {len(horses)} horses ===\n")

mismatches = []

for h in horses:
    hnum = h["horse_number"]
    hname = h["horse_name"]

    # Get horse detail
    url = f"http://localhost:5002/api/horse-detail/{race_id}/{hnum}"
    try:
        detail = json.loads(urllib.request.urlopen(url, timeout=30).read())
    except Exception as e:
        print(f"  #{hnum} {hname}: ERROR {e}")
        continue

    runs = detail.get("recent_runs", [])
    if not runs:
        print(f"  #{hnum} {hname}: No runs")
        continue

    # Check: do the runs make sense for this horse?
    # The API returns runs from get_horse_history which searches by horse_name
    # If there's a name collision or mismatch, the data will be wrong
    detail_name = detail.get("horse_name", "")
    
    # Show summary
    run_summary = []
    for r in runs[:3]:
        rn = r.get("race_name", "?")
        rv = r.get("venue", "?")
        rd = r.get("date", "?")
        rf = r.get("finish", "?")
        run_summary.append(f"{rd} {rv} {rn} {rf}着")

    print(f"  #{hnum} {hname} (detail_name={detail_name})")
    for s in run_summary:
        print(f"    {s}")
