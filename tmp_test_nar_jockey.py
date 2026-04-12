import json, urllib.request

payload = {
    "race_id": "20260405-水沢-1",
    "horses": ["パワームーブ", "キタスクワート", "エンジェルスラップ"],
    "horse_numbers": [1, 2, 3],
    "jockeys": ["坂井瑛音", "小林凌", "斉藤友香"],
    "posts": [1, 2, 3],
    "venue": "水沢",
    "race_number": 1,
    "distance": "ダ850m",
    "track_condition": "良",
}

req = urllib.request.Request(
    "http://localhost:8000/api/v2/analysis/jockey-analysis",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
print("=== Jockey Analysis for 水沢1R ===")
print(json.dumps(resp, ensure_ascii=False, indent=2)[:1500])
