"""Remove duplicate races from the knowledge file and report stats."""
import json, time
from datetime import datetime

path = "/tmp/unified_knowledge_cache.json"

print(f"[{datetime.now().isoformat()}] Loading knowledge file...")
start = time.time()
with open(path, "r") as f:
    data = json.load(f)
print(f"  Loaded in {time.time()-start:.1f}s")

horses = data.get("horses", {})
print(f"  Total horses: {len(horses)}")

total_dupes_removed = 0
affected_horses = 0

for name, hdata in horses.items():
    races = hdata.get("races", [])
    if len(races) <= 1:
        continue

    # Deduplicate by RACE_CODE
    seen_codes = set()
    unique_races = []
    dupes = 0
    for r in races:
        code = r.get("RACE_CODE", "")
        if not code:
            # No RACE_CODE - use date+venue+race_bango as key
            code = f"{r.get('KAISAI_NEN','')}{r.get('KAISAI_GAPPI','')}{r.get('KEIBAJO_CODE','')}{r.get('RACE_BANGO','')}"
        if code in seen_codes:
            dupes += 1
            continue
        seen_codes.add(code)
        unique_races.append(r)

    if dupes > 0:
        total_dupes_removed += dupes
        affected_horses += 1
        hdata["races"] = unique_races
        hdata["total_races"] = len(unique_races)
        if dupes >= 2:
            print(f"  {name}: {len(races)} -> {len(unique_races)} ({dupes} dupes removed)")

print(f"\n=== Summary ===")
print(f"  Affected horses: {affected_horses}")
print(f"  Total duplicates removed: {total_dupes_removed}")

# Save back
print(f"\nSaving cleaned file...")
data["metadata"]["deduped_at"] = datetime.now().isoformat()
start = time.time()
with open(path, "w") as f:
    json.dump(data, f, ensure_ascii=False)
print(f"  Saved in {time.time()-start:.1f}s")
print("Done!")
