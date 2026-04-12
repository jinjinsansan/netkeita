import json, urllib.request, urllib.parse

# Test JRA still works
rid = urllib.parse.quote("20260405-中山-1")
url = f"http://localhost:5002/api/race/{rid}/matrix"
m = json.loads(urllib.request.urlopen(url, timeout=120).read())
print(f"JRA race: {m.get('race_name')}")
print(f"venue: {m.get('venue')}")
print(f"is_local: {m.get('is_local')}")
print(f"horses: {len(m.get('horses', []))}")

# Test JRA horse detail with stable comment
url = f"http://localhost:5002/api/horse-detail/{rid}/1"
d = json.loads(urllib.request.urlopen(url, timeout=60).read())
print(f"\nHorse: #{d.get('horse_number')} {d.get('horse_name')}")
print(f"is_local: {d.get('is_local')}")
sc = d.get("stable_comment", {})
print(f"stable_comment exists: {bool(sc)}")
if sc:
    print(f"  mark: {sc.get('mark','-')}")
    print(f"  comment[:50]: {str(sc.get('comment',''))[:50]}")
cs = d.get("course_stats", {})
print(f"course_stats keys: {list(cs.keys())[:3]}")
