import json
import urllib.request

payload = {
    "race_id": "test",
    "horses": ["テスト馬A", "テスト馬B", "テスト馬C", "テスト馬D", "テスト馬E"],
    "horse_numbers": [1, 2, 3, 4, 5]
}

req = urllib.request.Request(
    "http://localhost:8000/api/v2/predictions/newspaper",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
res = urllib.request.urlopen(req, timeout=15)
print(res.read().decode())
