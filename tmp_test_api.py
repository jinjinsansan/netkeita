import json, urllib.request

url = "http://localhost:5002/api/horse-detail/20260404-%E4%B8%AD%E5%B1%B1-11/1"
data = json.loads(urllib.request.urlopen(url, timeout=30).read())

print("=== course_stats ===")
print(json.dumps(data.get("course_stats", {}), ensure_ascii=False, indent=2))

print("\n=== recent_runs[0] ===")
if data.get("recent_runs"):
    print(json.dumps(data["recent_runs"][0], ensure_ascii=False, indent=2))
else:
    print("NO RUNS")
