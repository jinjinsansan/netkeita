import json, urllib.request

# Test recent-runs
data = {
    "race_id": "20260404-中山-11",
    "horses": ["ファーヴェント", "ミニトランザット"],
    "horse_numbers": [8, 2],
    "venue": "中山",
    "distance": "芝1600m"
}
req = urllib.request.Request(
    "http://localhost:8000/api/v2/analysis/recent-runs",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req, timeout=60)
result = json.loads(resp.read().decode("utf-8"))
print("=== RECENT RUNS ===")
print(json.dumps(result, indent=2, ensure_ascii=False)[:3000])

# Test bloodline-analysis
data2 = {
    "race_id": "20260404-中山-11",
    "horses": ["ファーヴェント", "ミニトランザット"],
    "horse_numbers": [8, 2],
    "venue": "中山",
    "distance": "芝1600m"
}
req2 = urllib.request.Request(
    "http://localhost:8000/api/v2/analysis/bloodline-analysis",
    data=json.dumps(data2).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp2 = urllib.request.urlopen(req2, timeout=60)
result2 = json.loads(resp2.read().decode("utf-8"))
print("\n=== BLOODLINE ===")
print(json.dumps(result2, indent=2, ensure_ascii=False)[:3000])
