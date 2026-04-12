import json, urllib.request, urllib.parse, time
BASE = "https://bot.dlogicai.in/nk"

def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))

data = get_json("/api/races?date=20260405")
races = data["races"]
dims = ["total","speed","flow","jockey","bloodline","recent","track","ev"]

# full scan
zero_count = {d: 0 for d in dims}
total_horses = 0
bad_races = []

for i, r in enumerate(races):
    rid = r["race_id"]
    venue = r["venue"]
    rno = r["race_number"]
    lab = "NAR" if r.get("is_local") else "JRA"
    try:
        m = get_json(f"/api/race/{urllib.parse.quote(rid)}/matrix")
    except Exception as e:
        print(f"ERR {venue}{rno}: {e}")
        continue
    horses = m.get("horses", [])
    total_horses += len(horses)
    race_zeros = {d: 0 for d in dims}
    for h in horses:
        sc = h.get("scores", {}) or {}
        for d in dims:
            v = sc.get(d, 0) or 0
            try:
                if float(v) <= 0:
                    zero_count[d] += 1
                    race_zeros[d] += 1
            except:
                pass
    bad = {d: race_zeros[d] for d in dims if race_zeros[d] > 0}
    if bad:
        bad_races.append((lab, venue, rno, len(horses), bad))

print(f"Total races: {len(races)}, total horses: {total_horses}")
print(f"Zero count by dimension: {zero_count}")
print(f"Races with any zero: {len(bad_races)}")
for lab, v, r, n, bad in bad_races[:30]:
    print(f"  [{lab}] {v}{r}R ({n}頭): {bad}")
