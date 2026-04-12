import json, os, glob

# Find prefetch files
dirs = ["/root/dlogic-agent/data/prefetch", "/opt/dlogic/data/prefetch", "/opt/netkeita/data/prefetch"]
found = None
for d in dirs:
    if os.path.isdir(d):
        files = sorted(glob.glob(f"{d}/races_*.json"))
        if files:
            found = files[-1]
            print(f"Latest file: {found}")
            break

if not found:
    print("No prefetch file found")
    exit()

with open(found) as f:
    d = json.load(f)

races = d.get("races", [])
print(f"Total races: {len(races)}")

jra = [r for r in races if not r.get("is_local", False)]
nar = [r for r in races if r.get("is_local", False)]
print(f"JRA: {len(jra)}, NAR: {len(nar)}")

if nar:
    r = nar[0]
    print(f"\nNAR sample:")
    print(f"  venue: {r.get('venue')}")
    print(f"  race_id: {r.get('race_id')}")
    print(f"  race_name: {r.get('race_name')}")
    print(f"  distance: {r.get('distance')}")
    print(f"  horses[:3]: {r.get('horses', [])[:3]}")
    print(f"  horse_numbers[:3]: {r.get('horse_numbers', [])[:3]}")
    print(f"  jockeys[:3]: {r.get('jockeys', [])[:3]}")
    print(f"  has odds: {bool(r.get('odds'))}")
    print(f"  all keys: {list(r.keys())}")

    # Count unique venues
    venues = {}
    for r in nar:
        v = r.get("venue", "")
        venues[v] = venues.get(v, 0) + 1
    print(f"\nNAR venues: {venues}")
else:
    print("No NAR races in this file")
