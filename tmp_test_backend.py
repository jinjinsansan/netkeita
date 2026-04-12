import json, urllib.request

payload = {
    "race_id": "test",
    "horses": ["シャドウメテオ"],
    "horse_numbers": [1],
    "jockeys": ["丹内 祐次"],
    "posts": [1],
    "venue": "中山",
    "race_number": 11,
    "distance": "芝2000m",
    "track_condition": "良",
}

req = urllib.request.Request(
    "http://localhost:8000/api/v2/predictions/full-scores",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
print(json.dumps(resp, ensure_ascii=False, indent=2)[:800])
