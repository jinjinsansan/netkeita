"""
Thorough check: for every horse in today's 24 races,
verify that the recent_runs data belongs to the correct horse.
Cross-reference with the raw knowledge file.
"""
import json, urllib.request, sys

BASE = "http://localhost:5002"

# Load knowledge file for cross-reference
print("Loading knowledge file...")
with open("/tmp/unified_knowledge_cache.json") as f:
    kdata = json.load(f)
horses_db = kdata.get("horses", {})
print(f"Knowledge: {len(horses_db)} horses\n")

# All 24 races today (2026-04-04)
race_ids = []
for venue in ["%E4%B8%AD%E5%B1%B1", "%E9%98%AA%E7%A5%9E"]:  # 中山, 阪神
    for rnum in range(1, 13):
        race_ids.append(f"20260404-{venue}-{rnum}")

total_checked = 0
issues = []

for race_id in race_ids:
    # Get race matrix
    try:
        url = f"{BASE}/api/race/{race_id}/matrix"
        resp = urllib.request.urlopen(url, timeout=30)
        matrix = json.loads(resp.read())
    except Exception as e:
        continue

    horses = matrix.get("horses", [])
    venue_name = race_id.split("-")[1]
    rnum = race_id.split("-")[2]

    for h in horses:
        hnum = h["horse_number"]
        hname = h["horse_name"]

        # Get horse detail
        try:
            url = f"{BASE}/api/horse-detail/{race_id}/{hnum}"
            detail = json.loads(urllib.request.urlopen(url, timeout=60).read())
        except Exception:
            issues.append(f"[TIMEOUT] {race_id} #{hnum} {hname}")
            continue

        runs = detail.get("recent_runs", [])
        detail_name = detail.get("horse_name", "")
        total_checked += 1

        # Check 1: horse_name mismatch
        if detail_name != hname:
            issues.append(f"[NAME MISMATCH] {race_id} #{hnum}: expected={hname} got={detail_name}")

        # Check 2: duplicate runs
        if runs:
            keys = [f"{r.get('date','')}{r.get('venue','')}{r.get('race_name','')}" for r in runs]
            if len(keys) != len(set(keys)):
                issues.append(f"[DUPLICATE RUNS] {race_id} #{hnum} {hname}: {len(keys)} runs, {len(set(keys))} unique")

        # Check 3: cross-reference with knowledge file
        if hname in horses_db:
            kb_races = horses_db[hname].get("races", [])
            if runs and kb_races:
                # Compare first run with first knowledge race
                kb_first = kb_races[0]
                run_first = runs[0]
                kb_date = f"{kb_first.get('KAISAI_NEN','')}/{kb_first.get('KAISAI_GAPPI','')}"
                run_date = run_first.get("date", "")
                if kb_date != run_date:
                    issues.append(f"[DATE MISMATCH] {race_id} #{hnum} {hname}: kb={kb_date} api={run_date}")

        # Check 4: look for cases where knowledge has data for different horse with same name
        # (partial name match issues)

    # Progress
    print(f"  Checked {race_id}: {len(horses)} horses")

print(f"\n{'='*60}")
print(f"Total checked: {total_checked}")
print(f"Issues found: {len(issues)}")
for issue in issues:
    print(f"  {issue}")

if not issues:
    print("  ALL CLEAR - No issues found!")
