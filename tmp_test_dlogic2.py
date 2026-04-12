import json
import urllib.request

# まず川崎11Rのエントリーを取得
url = "https://bot.dlogicai.in/nk/api/race/20260408-%E5%B7%9D%E5%B4%8E-11/entries"
res = urllib.request.urlopen(url, timeout=15)
race = json.loads(res.read())

entries = race["entries"]
horse_numbers = [e["horse_number"] for e in entries]
horse_names   = [e.get("horse_name", "") for e in entries]
jockeys       = [e.get("jockey", "") for e in entries]
posts         = [e.get("post", 0) for e in entries]
odds          = [float(e.get("odds", 10.0)) for e in entries]

payload = {
    "race_id": race["race_id"],
    "horses": horse_names,
    "horse_numbers": horse_numbers,
    "venue": race.get("venue", ""),
    "race_number": race.get("race_number", 0),
    "jockeys": jockeys,
    "posts": posts,
    "distance": race.get("distance", ""),
    "track_condition": race.get("track_condition", "良"),
    "odds": odds,
}

req = urllib.request.Request(
    "http://localhost:8000/api/v2/predictions/newspaper",
    data=json.dumps(payload, ensure_ascii=False).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
res = urllib.request.urlopen(req, timeout=15)
data = json.loads(res.read())

horse_map = {e["horse_number"]: e["horse_name"] for e in entries}

for engine in ["dlogic", "metalogic", "viewlogic", "ilogic"]:
    top5 = data.get(engine, [])
    names = [f"{n}.{horse_map.get(n,'?')}" for n in top5]
    print(f"{engine}: {names}")
