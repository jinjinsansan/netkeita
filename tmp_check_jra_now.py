import json, urllib.request, urllib.parse

# Test JRA Nakayama 11R
rid = urllib.parse.quote("20260405-中山-11")
url = f"http://localhost:5002/api/race/{rid}/matrix"
m = json.loads(urllib.request.urlopen(url, timeout=180).read())

print(f"race: {m.get('race_name')}")
print(f"horses: {len(m.get('horses', []))}")

for h in m.get("horses", [])[:3]:
    print(f"  #{h['horse_number']} {h['horse_name']}: scores={h['scores']}")

# Also check that jockey_data has entries
jd = m.get("jockey_data", {})
print(f"\njockey_post_stats: {len(jd.get('jockey_post_stats', {}))}")
print(f"jockey_course_stats: {len(jd.get('jockey_course_stats', {}))}")
