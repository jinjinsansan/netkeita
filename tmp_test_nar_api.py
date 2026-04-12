import json, urllib.request, sys

# Test races endpoint
url = "http://localhost:5002/api/races?date=20260405"
d = json.loads(urllib.request.urlopen(url, timeout=30).read())
print(f"Total: {d['count']} races")

venues = {}
for r in d["races"]:
    v = r.get("venue", "?")
    is_local = r.get("is_local", False)
    key = f"{v}({'NAR' if is_local else 'JRA'})"
    venues[key] = venues.get(key, 0) + 1

print(f"Venues:")
for k, v in sorted(venues.items()):
    print(f"  {k}: {v}")

nar_count = sum(1 for r in d["races"] if r.get("is_local"))
jra_count = sum(1 for r in d["races"] if not r.get("is_local"))
print(f"\nJRA: {jra_count}, NAR: {nar_count}")

# Test matrix endpoint for a NAR race
nar_races = [r for r in d["races"] if r.get("is_local")]
if nar_races:
    sample = nar_races[0]
    rid = sample["race_id"]
    print(f"\n=== Testing NAR race matrix: {rid} ===")
    url = f"http://localhost:5002/api/race/{urllib.parse.quote(rid)}/matrix"
    try:
        import urllib.parse
        url = f"http://localhost:5002/api/race/{urllib.parse.quote(rid)}/matrix"
        m = json.loads(urllib.request.urlopen(url, timeout=120).read())
        print(f"  race_name: {m.get('race_name')}")
        print(f"  venue: {m.get('venue')}")
        print(f"  is_local: {m.get('is_local')}")
        print(f"  horses: {len(m.get('horses', []))}")
        if m.get("horses"):
            h = m["horses"][0]
            print(f"  sample horse #{h['horse_number']} {h['horse_name']}")
            print(f"    scores.total={h['scores']['total']}")
    except Exception as e:
        print(f"  ERROR: {e}")
