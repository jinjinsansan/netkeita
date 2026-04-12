python3 << 'PYEOF'
import json, urllib.request

url = "http://localhost:8000/api/v2/predictions/full-scores"
payload = {
    "race_id": "20260404-中山-11",
    "horses": ["ゾンニッヒ", "ミニトランザット", "エンペラーズソード"],
    "horse_numbers": [1, 2, 3],
    "venue": "中山",
    "distance": "芝1600m",
    "track_condition": "良"
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode("utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()
PYEOF
