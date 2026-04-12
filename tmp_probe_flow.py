import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

# 中山11R
data = get_json("/api/races?date=20260405")
rid = None
for r in data["races"]:
    if r["venue"] == "中山" and r["race_number"] == 11:
        rid = r["race_id"]; break

print("race_id:", rid)
m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
horses = m.get("horses", [])
print(f"horses: {len(horses)}")

# flow per horse
dims = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
for h in horses:
    sc = h["scores"]
    print(f"  #{h['horse_number']:02d} {h['horse_name'][:10]:<10s} "
          f"total={sc['total']:6.1f} speed={sc['speed']:6.1f} flow={sc['flow']:6.1f} "
          f"jockey={sc['jockey']:6.1f} blood={sc['bloodline']:6.1f} recent={sc['recent']:6.1f} "
          f"ev={sc['ev']:6.2f}")

# jockey names
jockeys = [h.get("jockey","") for h in horses]
print("jockeys:", jockeys)
