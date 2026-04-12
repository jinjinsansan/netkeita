"""Check ev score sanity - is it giving meaningful differentiation?"""
import json, urllib.request, urllib.parse
BASE = "https://bot.dlogicai.in/nk"
def get_json(p):
    with urllib.request.urlopen(BASE + p, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))
data = get_json("/api/races?date=20260405")
# Sample a few races for ev check
import collections
ev_stats = []
for r in data["races"][:20]:
    m = get_json(f"/api/race/{urllib.parse.quote(r['race_id'])}/matrix")
    evs = [h["scores"]["ev"] for h in m["horses"]]
    ev_stats.append({
        "venue": r["venue"], "rn": r["race_number"],
        "min": min(evs), "max": max(evs), 
        "range": max(evs)-min(evs),
        "median": sorted(evs)[len(evs)//2],
        "is_local": r.get("is_local", False),
    })
for s in ev_stats:
    print(s)
