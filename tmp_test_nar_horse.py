import json, urllib.request, urllib.parse

# Test horse-detail for a NAR horse
rid = urllib.parse.quote("20260405-水沢-1")
url = f"http://localhost:5002/api/horse-detail/{rid}/1"
d = json.loads(urllib.request.urlopen(url, timeout=120).read())

print(f"Horse: #{d.get('horse_number')} {d.get('horse_name')}")
print(f"is_local: {d.get('is_local')}")
print(f"stable_comment: {d.get('stable_comment')}")
print(f"course_stats: {d.get('course_stats')}")
print(f"\nrecent_runs ({len(d.get('recent_runs', []))}):")
for r in d.get("recent_runs", [])[:5]:
    print(f"  {r.get('date')} {r.get('venue')} {r.get('race_name','?')} {r.get('finish','?')}着")

bl = d.get("bloodline", {})
print(f"\nbloodline: sire={bl.get('sire','-')} bms={bl.get('broodmare_sire','-')}")
