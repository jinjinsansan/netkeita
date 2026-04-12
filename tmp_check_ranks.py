import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"
def get_json(p):
    with urllib.request.urlopen(BASE + p, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))
data = get_json("/api/races?date=20260405")
for r in data["races"]:
    if r["venue"] == "中山" and r["race_number"] == 11:
        rid = r["race_id"]; break
m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
import collections
dims = ["total","speed","flow","jockey","bloodline","recent","track","ev"]
print(f"horses: {len(m['horses'])}")
for d in dims:
    ranks = [h["ranks"].get(d, "?") for h in m["horses"]]
    c = collections.Counter(ranks)
    print(f"  {d}: {dict(c)}")
